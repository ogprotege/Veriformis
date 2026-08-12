import XCTest
@testable import Veriformis

final class CLIBridgeTests: XCTestCase {
    @MainActor
    func testProcessRunnerSuspendsWithoutBlockingMainActor() async throws {
        let cli = shellCLI()
        let controller = CLIProcessController(terminationGrace: 0.1)
        let started = Date()
        let task = Task {
            try await cli.run(
                arguments: ["-c", "sleep 0.3; printf 'done\\n'"],
                controller: controller
            )
        }

        try await Task.sleep(nanoseconds: 50_000_000)
        XCTAssertLessThan(Date().timeIntervalSince(started), 0.2)
        let result = try await task.value
        XCTAssertEqual(result.exitCode, 0)
        XCTAssertTrue(result.combinedOutput.contains("done"))
    }

    func testProcessRunnerDrainsHighVolumeOutputAndBoundsRetention() async throws {
        let cli = shellCLI()
        let controller = CLIProcessController(
            terminationGrace: 0.1,
            maxRetainedOutputBytes: 64 * 1024
        )
        let script = """
        i=0
        while [ "$i" -lt 5000 ]; do
          printf 'out-%04d-abcdefghijklmnopqrstuvwxyz0123456789\\n' "$i"
          printf 'err-%04d-abcdefghijklmnopqrstuvwxyz0123456789\\n' "$i" >&2
          i=$((i + 1))
        done
        """

        let result = try await cli.run(
            arguments: ["-c", script],
            controller: controller
        )

        XCTAssertEqual(result.exitCode, 0)
        XCTAssertTrue(result.outputTruncated)
        XCTAssertLessThanOrEqual(result.combinedOutput.utf8.count, 64 * 1024)
        XCTAssertTrue(result.combinedOutput.contains("out-4999"))
        XCTAssertTrue(result.combinedOutput.contains("err-4999"))
    }

    func testProcessRunnerReplacesInvalidUTF8() async throws {
        let result = try await shellCLI().run(
            arguments: ["-c", "printf '\\377bad\\n'"],
            controller: CLIProcessController()
        )

        XCTAssertEqual(result.exitCode, 0)
        XCTAssertTrue(result.combinedOutput.contains("\u{FFFD}bad"))
    }

    func testProcessRunnerCancellationTerminatesGracefulChild() async throws {
        let controller = CLIProcessController(terminationGrace: 0.2)
        let task = Task {
            try await shellCLI().run(
                arguments: ["-c", "trap 'exit 0' TERM; while :; do sleep 0.02; done"],
                controller: controller
            )
        }
        try await Task.sleep(nanoseconds: 80_000_000)
        controller.cancel()

        let result = try await task.value
        let cancellation = try XCTUnwrap(result.cancellation)
        XCTAssertNotNil(cancellation.processIdentifier)
        XCTAssertFalse(cancellation.terminationEscalated)
        XCTAssertFalse(controller.hasActiveProcess)
    }

    func testProcessRunnerCancellationBeforeLaunchReturnsReceipt() async throws {
        let controller = CLIProcessController(terminationGrace: 0.05)
        let task = Task {
            try await shellCLI().run(
                arguments: ["-c", "sleep 5"],
                controller: controller
            )
        }
        task.cancel()

        let result = try await task.value
        XCTAssertNotNil(result.cancellation)
        XCTAssertFalse(controller.hasActiveProcess)
    }

    func testProcessControllerRecoversForAnotherRunAfterCancellation() async throws {
        let controller = CLIProcessController(terminationGrace: 0.05)
        let cancelledTask = Task {
            try await shellCLI().run(
                arguments: ["-c", "trap 'exit 0' TERM; while :; do sleep 0.02; done"],
                controller: controller
            )
        }
        try await Task.sleep(nanoseconds: 60_000_000)
        controller.cancel()
        let cancelled = try await cancelledTask.value
        XCTAssertNotNil(cancelled.cancellation)

        let recovered = try await shellCLI().run(
            arguments: ["-c", "printf 'recovered\\n'"],
            controller: controller
        )
        XCTAssertEqual(recovered.exitCode, 0)
        XCTAssertTrue(recovered.combinedOutput.contains("recovered"))
        XCTAssertNil(recovered.cancellation)
    }

    func testProcessRunnerCancellationEscalatesWhenTermIgnored() async throws {
        let controller = CLIProcessController(terminationGrace: 0.05)
        let task = Task {
            try await shellCLI().run(
                arguments: ["-c", "trap '' TERM; while :; do :; done"],
                controller: controller
            )
        }
        try await Task.sleep(nanoseconds: 80_000_000)
        controller.cancel()

        let result = try await task.value
        let cancellation = try XCTUnwrap(result.cancellation)
        XCTAssertTrue(cancellation.terminationEscalated)
        XCTAssertFalse(controller.hasActiveProcess)
    }

    func testCancellationReceiptRoundTripsAndCarriesRecoveryFacts() throws {
        let receipt = RunCancellationReceipt(
            requestedAt: Date(timeIntervalSince1970: 42),
            stage: WorkbenchStage.chunk.rawValue,
            processIdentifier: 123,
            terminationStatus: 15,
            terminationEscalated: false,
            completedStages: [WorkbenchStage.parse.rawValue, WorkbenchStage.clean.rawValue],
            workspaceRetained: true,
            outputWasTruncated: true
        )
        let encoded = try JSONEncoder().encode(receipt)
        XCTAssertEqual(try JSONDecoder().decode(RunCancellationReceipt.self, from: encoded), receipt)
        XCTAssertTrue(WorkbenchError.cancelled(receipt).localizedDescription.contains("workspace retained"))
    }

    func testLegacyHistoryWithoutCancellationReceiptStillDecodes() throws {
        let encoded = try JSONEncoder().encode(historyEntry(writeAptusHandoff: nil))
        var json = try XCTUnwrap(JSONSerialization.jsonObject(with: encoded) as? [String: Any])
        json.removeValue(forKey: "cancellationReceipt")
        let legacy = try JSONSerialization.data(withJSONObject: json)
        let decoded = try JSONDecoder().decode(RunHistoryEntry.self, from: legacy)
        XCTAssertNil(decoded.cancellationReceipt)
    }

    @MainActor
    func testApplicationQuitWaitsForRunCancellationBeforeReplying() {
        let coordinator = ApplicationTerminationCoordinator()
        var finishCancellation: (() -> Void)?
        var replied = false

        let decision = coordinator.prepareForTermination(
            isRunActive: true,
            cancel: { finishCancellation = $0 },
            reply: { replied = true }
        )

        XCTAssertEqual(decision, .terminateLater)
        XCTAssertTrue(coordinator.awaitingCancellation)
        XCTAssertFalse(replied)
        finishCancellation?()
        XCTAssertFalse(coordinator.awaitingCancellation)
        XCTAssertTrue(replied)
    }

    @MainActor
    func testApplicationQuitTerminatesImmediatelyWithoutActiveRun() {
        let coordinator = ApplicationTerminationCoordinator()
        let decision = coordinator.prepareForTermination(
            isRunActive: false,
            cancel: { _ in XCTFail("cancel should not be requested") },
            reply: { XCTFail("deferred reply should not be used") }
        )
        XCTAssertEqual(decision, .terminateNow)
    }

    @MainActor
    func testWorkbenchCancellationProducesAReceiptAtEveryExecutableStage() async throws {
        for stage in WorkbenchStage.workbenchRunStages {
            let root = FileManager.default.temporaryDirectory
                .appendingPathComponent("veriformis-cancel-\(UUID().uuidString)")
            let output = root.appendingPathComponent("output", isDirectory: true)
            let support = root.appendingPathComponent("support", isDirectory: true)
            try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)
            defer { try? FileManager.default.removeItem(at: root) }

            let source = root.appendingPathComponent("source.txt")
            try Data("source\n".utf8).write(to: source)
            let executable = root.appendingPathComponent("fake-veriformis")
            let script = """
            #!/bin/sh
            stage="$1"
            if [ "$stage" = "seal" ]; then
              printf 'manifest SHA-256: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\\n'
            fi
            if [ "$stage" = "\(stage.rawValue)" ]; then
              trap 'exit 0' TERM INT
              while :; do sleep 0.02; done
            fi
            exit 0
            """
            try Data(script.utf8).write(to: executable)
            try FileManager.default.setAttributes(
                [.posixPermissions: 0o755],
                ofItemAtPath: executable.path
            )

            let suiteName = "veriformis-tests-\(UUID().uuidString)"
            let defaults = try XCTUnwrap(UserDefaults(suiteName: suiteName))
            defaults.set(output.path, forKey: "veriformis.workbench.defaultOutput")
            defer { defaults.removePersistentDomain(forName: suiteName) }
            let workbench = WorkbenchViewModel(
                cli: VeriformisCLI(executableURL: executable, prefixArguments: []),
                defaults: defaults,
                supportDirectory: support
            )
            workbench.sourceURLs = [source]
            workbench.sourceRootURL = root
            workbench.outputDirectoryURL = output
            workbench.compile()

            var reachedStage = false
            for _ in 0 ..< 300 {
                if workbench.isRunning, workbench.currentStage == stage {
                    reachedStage = true
                    break
                }
                try await Task.sleep(nanoseconds: 10_000_000)
            }
            XCTAssertTrue(reachedStage, "did not reach \(stage.rawValue)")
            workbench.cancelCompile()

            for _ in 0 ..< 300 where workbench.isRunning {
                try await Task.sleep(nanoseconds: 10_000_000)
            }
            XCTAssertFalse(workbench.isRunning, "did not cancel \(stage.rawValue)")
            XCTAssertEqual(workbench.lastCancellation?.stage, stage.rawValue)
            XCTAssertEqual(workbench.runHistory.first?.status, .cancelled)
            XCTAssertEqual(
                workbench.runHistory.first?.cancellationReceipt,
                workbench.lastCancellation
            )
            XCTAssertTrue(workbench.lastCancellation?.workspaceRetained == true)
        }
    }

    func testCompilePlanOrderAndArguments() {
        let sources = [
            URL(fileURLWithPath: "/data/raw/a.txt"),
            URL(fileURLWithPath: "/data/raw/b.md"),
        ]
        let root = URL(fileURLWithPath: "/data/raw")
        let workspace = URL(fileURLWithPath: "/tmp/ws")
        let bundle = URL(fileURLWithPath: "/tmp/out.vfbundle")

        let plan = VeriformisCLI.compilePlan(
            sources: sources,
            sourceRoot: root,
            workspace: workspace,
            bundle: bundle,
            objective: .continuation,
            allowEmptyEvaluation: true,
            splitRatioPPM: 400_000,
            includeHandoff: true
        )

        XCTAssertEqual(plan.map(\.stage), [
            .parse, .clean, .chunk, .construct, .curate, .split, .format, .validate, .seal,
        ])
        XCTAssertEqual(plan[0].arguments.first, "parse")
        XCTAssertTrue(plan[0].arguments.contains("--source-root"))
        XCTAssertTrue(plan[3].arguments.contains("continuation"))
        XCTAssertTrue(plan[3].arguments.contains("400000"))
        XCTAssertTrue(plan[4].arguments.contains("--allow-empty-evaluation"))
        XCTAssertEqual(
            plan[8].arguments,
            ["seal", workspace.path, "-o", bundle.path, "--aptus-handoff"]
        )
    }

    func testCompilePlanStandaloneModeEmitsNoAptusFlag() {
        let workspace = URL(fileURLWithPath: "/tmp/ws")
        let bundle = URL(fileURLWithPath: "/tmp/b.vfbundle")
        let plan = VeriformisCLI.compilePlan(
            sources: [URL(fileURLWithPath: "/data/a.txt")],
            sourceRoot: URL(fileURLWithPath: "/data"),
            workspace: workspace,
            bundle: bundle,
            objective: .fullText,
            allowEmptyEvaluation: false,
            splitRatioPPM: 500_000
        )
        XCTAssertEqual(plan.last!.arguments, ["seal", workspace.path, "-o", bundle.path])
        XCTAssertFalse(plan.last!.arguments.contains { $0.lowercased().contains("aptus") })
    }

    func testWorkbenchAndLegacyHistoryDefaultToStandalone() throws {
        XCTAssertFalse(WorkbenchViewModel.defaultWriteAptusHandoff)
        let data = try JSONEncoder().encode(historyEntry(writeAptusHandoff: nil))
        let json = try XCTUnwrap(
            JSONSerialization.jsonObject(with: data) as? [String: Any]
        )
        XCTAssertNil(json["writeAptusHandoff"])
        let decoded = try JSONDecoder().decode(RunHistoryEntry.self, from: data)
        XCTAssertFalse(decoded.requestsAptusHandoff)
    }

    func testHistoryPreservesExplicitAptusOptIn() throws {
        let data = try JSONEncoder().encode(historyEntry(writeAptusHandoff: true))
        let json = try XCTUnwrap(
            JSONSerialization.jsonObject(with: data) as? [String: Any]
        )
        XCTAssertEqual(json["writeAptusHandoff"] as? Bool, true)
        let decoded = try JSONDecoder().decode(RunHistoryEntry.self, from: data)
        XCTAssertTrue(decoded.requestsAptusHandoff)
    }

    func testManifestSHAExtraction() {
        let log = """
        sealed bundle: /tmp/out.vfbundle
        manifest SHA-256: abcdef0123456789
        verification grade: external_digest
        """
        XCTAssertEqual(
            WorkbenchViewModel.extractManifestSHA256(from: log),
            "abcdef0123456789"
        )
    }

    func testAssignmentDigestExtraction() {
        let log = """
        aptus handoff: /tmp/out.vfbundle.aptus-handoff.json
        assignment digest: deadbeefcafebabe
        """
        XCTAssertEqual(
            WorkbenchViewModel.extractAssignmentDigest(from: log),
            "deadbeefcafebabe"
        )
    }

    func testArchiveDigestExtraction() {
        XCTAssertEqual(
            WorkbenchViewModel.extractArchiveSHA256(
                from: "archive SHA-256: 1234abcdef\nverification grade: external_digest"
            ),
            "1234abcdef"
        )
    }

    func testMakeFailureCapturesExitCodeAndStage() {
        let error = WorkbenchError.processFailed(
            stage: "construct",
            exitCode: 2,
            message: "boom\nline2"
        )
        let failure = WorkbenchViewModel.makeFailure(
            error: error,
            logLines: ["a", "b", "c"],
            workspace: URL(fileURLWithPath: "/tmp/ws"),
            logFile: nil
        )
        XCTAssertEqual(failure.stage, "construct")
        XCTAssertEqual(failure.exitCode, 2)
        XCTAssertTrue(failure.summary.contains("exit 2"))
        XCTAssertEqual(failure.lastLogLines, ["a", "b", "c"])
    }

    func testPipelineStageCountIsNine() {
        XCTAssertEqual(WorkbenchStage.pipelineStages.count, 9)
        XCTAssertFalse(WorkbenchStage.pipelineStages.contains(.verify))
    }

    func testObjectiveSubtitlesAreNonEmpty() {
        for objective in TrainingObjective.allCases {
            XCTAssertFalse(objective.subtitle.isEmpty, objective.rawValue)
        }
    }

    func testMissingCLIErrorMentionsPrerequisites() throws {
        let message = WorkbenchError.missingCLI.localizedDescription
        XCTAssertTrue(message.contains("uv sync"))
        XCTAssertTrue(message.contains("VERIFORMIS_CLI"))
    }

    func testMissingCLIOverrideFailsWithTypedRecoveryError() {
        XCTAssertThrowsError(
            try VeriformisCLI.resolve(
                repositoryRoot: URL(fileURLWithPath: "/definitely/not/a/repository"),
                environment: ["VERIFORMIS_CLI": "/definitely/not/veriformis"]
            )
        ) { error in
            XCTAssertEqual(error as? WorkbenchError, .missingCLI)
        }
    }

    func testDefaultSourceRootForSingleFileIsParentDirectory() {
        let file = URL(fileURLWithPath: "/Users/biscuit/docs/encyclical.md")
        let root = WorkbenchViewModel.defaultSourceRoot(for: [file])
        XCTAssertEqual(root?.path, "/Users/biscuit/docs")
        XCTAssertNotEqual(root?.path, file.path)
        XCTAssertFalse(root?.path.hasPrefix("//") ?? true)
    }

    func testDefaultSourceRootForSiblingFilesIsSharedParent() {
        let a = URL(fileURLWithPath: "/data/raw/corpus/a.txt")
        let b = URL(fileURLWithPath: "/data/raw/corpus/b.md")
        let root = WorkbenchViewModel.defaultSourceRoot(for: [a, b])
        XCTAssertEqual(root?.path, "/data/raw/corpus")
    }

    func testDefaultSourceRootForNestedFilesIsCommonAncestor() {
        let a = URL(fileURLWithPath: "/data/raw/en/a.md")
        let b = URL(fileURLWithPath: "/data/raw/la/b.md")
        let root = WorkbenchViewModel.defaultSourceRoot(for: [a, b])
        XCTAssertEqual(root?.path, "/data/raw")
    }

    func testResolveFindsRepoVenvOrUvWhenRootProvided() throws {
        // Walk from this source file up to the repository root (…/macos/Tests → repo).
        var dir = URL(fileURLWithPath: #filePath).deletingLastPathComponent()
        var root: URL?
        for _ in 0 ..< 6 {
            let marker = dir.appendingPathComponent("pyproject.toml")
            if FileManager.default.fileExists(atPath: marker.path) {
                root = dir
                break
            }
            dir.deleteLastPathComponent()
        }
        guard let root else {
            throw XCTSkip("Could not locate repo root from test file path")
        }
        let cli = try VeriformisCLI.resolve(repositoryRoot: root)
        XCTAssertTrue(
            FileManager.default.isExecutableFile(atPath: cli.executableURL.path),
            "expected executable at \(cli.executableURL.path)"
        )
    }

    private func historyEntry(writeAptusHandoff: Bool?) -> RunHistoryEntry {
        RunHistoryEntry(
            id: UUID(),
            startedAt: Date(timeIntervalSince1970: 0),
            finishedAt: Date(timeIntervalSince1970: 1),
            status: .succeeded,
            objective: TrainingObjective.fullText.rawValue,
            primarySourceName: "a.txt",
            sourcePaths: ["/data/a.txt"],
            workspacePath: "/tmp/ws",
            bundlePath: "/tmp/out.vfbundle",
            handoffPath: writeAptusHandoff == true
                ? "/tmp/out.vfbundle.aptus-handoff.json"
                : nil,
            logFilePath: nil,
            manifestSHA256: nil,
            assignmentDigest: nil,
            errorSummary: nil,
            sourceRootPath: "/data",
            allowEmptyEvaluation: true,
            writeAptusHandoff: writeAptusHandoff,
            splitRatioPPM: 400_000,
            failedStage: nil,
            exitCode: nil,
            cancellationReceipt: nil,
            transportArchivePath: nil,
            transportArchiveSHA256: nil
        )
    }

    private func shellCLI() -> VeriformisCLI {
        VeriformisCLI(
            executableURL: URL(fileURLWithPath: "/bin/sh"),
            prefixArguments: []
        )
    }
}
