import CryptoKit
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
        XCTAssertTrue(result.standardOutputTruncated)
        XCTAssertTrue(result.standardErrorTruncated)
        XCTAssertTrue(result.standardOutput.contains("out-4999"))
        XCTAssertTrue(result.standardError.contains("err-4999"))
    }

    func testProcessRunnerSeparatesStreamsAndRetainsCombinedCompatibility() async throws {
        let result = try await shellCLI().run(
            arguments: ["-c", "printf 'stdout-only\\n'; printf 'stderr-only\\n' >&2"],
            controller: CLIProcessController()
        )

        XCTAssertEqual(result.exitCode, 0)
        XCTAssertEqual(result.standardOutput, "stdout-only\n")
        XCTAssertEqual(result.standardError, "stderr-only\n")
        XCTAssertTrue(result.combinedOutput.contains("stdout-only"))
        XCTAssertTrue(result.combinedOutput.contains("stderr-only"))
        XCTAssertFalse(result.standardOutputTruncated)
        XCTAssertFalse(result.standardErrorTruncated)
        XCTAssertFalse(result.outputTruncated)
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
            stage: WorkbenchStage.format.rawValue,
            processIdentifier: 123,
            terminationStatus: 15,
            terminationEscalated: false,
            completedStages: [WorkbenchStage.split.rawValue, WorkbenchStage.format.rawValue],
            workspaceRetained: true,
            outputWasTruncated: true
        )
        let encoded = try JSONEncoder().encode(receipt)
        let decoded = try JSONDecoder().decode(RunCancellationReceipt.self, from: encoded)
        XCTAssertEqual(decoded, receipt)
        XCTAssertEqual(decoded.stage, "format")
        XCTAssertEqual(decoded.stageTitle, "Lower rows")
        XCTAssertEqual(decoded.completedStages, ["split", "format"])
        XCTAssertEqual(decoded.completedStageTitles, ["Split", "Lower rows"])
        let description = WorkbenchError.cancelled(decoded).localizedDescription
        XCTAssertTrue(description.contains("Lower rows"))
        XCTAssertTrue(description.contains("workspace retained"))
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
            if [ "$stage" = "preflight" ]; then
              \(try compilePreflightHeredoc())
              exit 0
            fi
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
            workbench.applyCatalogs(
                goals: try JSONDecoder().decode(GoalCatalog.self, from: goalCatalogData()),
                presets: try JSONDecoder().decode(RecipePresetCatalog.self, from: recipePresetsData())
            )
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

    // MARK: - Compile preflight (Phase 6.5)

    func testCompilePreflightDecodesCompleteStrictResponse() throws {
        let report = try JSONDecoder().decode(
            CompilePreflight.self,
            from: compilePreflightData()
        )

        XCTAssertEqual(report.schemaID, "veriformis.compile-preflight/v1")
        XCTAssertTrue(report.admitted)
        XCTAssertEqual(report.evaluatedThrough, .split)
        XCTAssertEqual(report.counts.sourceCount, 1)
        XCTAssertEqual(report.counts.admittedSourceCount, 1)
        XCTAssertEqual(report.selection.resolved?.goalID, "continue-a-passage")
        XCTAssertEqual(report.selection.resolved?.objective, .continuation)
        XCTAssertEqual(report.selection.resolved?.rowSchema, "prompt_completion")
        let source = try XCTUnwrap(report.sources.first)
        XCTAssertEqual(source.inputFamily, "plain-text")
        XCTAssertEqual(source.parserID, "plain-text-v1")
        XCTAssertEqual(source.parserStatus, .complete)
        XCTAssertEqual(source.evidenceStatus, .available)
        XCTAssertTrue(source.admitted)
        XCTAssertEqual(source.diagnosticCounts.first?.count, 1)
        XCTAssertEqual(source.diagnostics.first?.lossKind, "none")
        XCTAssertEqual(report.expectedExclusions.first?.status, .excluded)
        XCTAssertEqual(report.knownLimitations.first?.code, "point-in-time-source-capture")
    }

    func testCompilePreflightAcceptsContractValidLogicalPathWhitespace() throws {
        let report = try JSONDecoder().decode(
            CompilePreflight.self,
            from: compilePreflightData { payload in
                var sources = payload["sources"] as! [[String: Any]]
                sources[0]["logical_path"] = " leading and trailing .txt "
                payload["sources"] = sources
            }
        )

        XCTAssertEqual(report.sources.first?.logicalPath, " leading and trailing .txt ")
    }

    func testCompilePreflightRejectsKeyAndEnumDrift() throws {
        XCTAssertThrowsError(
            try JSONDecoder().decode(
                CompilePreflight.self,
                from: compilePreflightData { $0.removeValue(forKey: "known_limitations") }
            )
        ) { error in
            XCTAssertEqual(
                error as? CompilePreflightError,
                .invalidKeySet(
                    scope: "response",
                    missing: ["known_limitations"],
                    unexpected: []
                )
            )
        }
        XCTAssertThrowsError(
            try JSONDecoder().decode(
                CompilePreflight.self,
                from: compilePreflightData { payload in
                    var sources = payload["sources"] as! [[String: Any]]
                    sources[0]["parser_status"] = "probably"
                    payload["sources"] = sources
                }
            )
        )
        XCTAssertThrowsError(
            try JSONDecoder().decode(
                CompilePreflight.self,
                from: compilePreflightData { payload in
                    var counts = payload["counts"] as! [String: Any]
                    counts["guessed_count"] = 1
                    payload["counts"] = counts
                }
            )
        ) { error in
            XCTAssertEqual(
                error as? CompilePreflightError,
                .invalidKeySet(
                    scope: "counts",
                    missing: [],
                    unexpected: ["guessed_count"]
                )
            )
        }
    }

    func testCompilePreflightDecodesSelectionRefusalWithoutInventingResolution() throws {
        let data = try compilePreflightData(admitted: false) { payload in
            payload["captured_source_digest"] = NSNull()
            payload["evaluated_through"] = "selection"
            payload["sources"] = []
            payload["missing_evidence"] = []
            var counts = payload["counts"] as! [String: Any]
            for key in Array(counts.keys) {
                counts[key] = 0
            }
            payload["counts"] = counts
            payload["selection"] = [
                "requested_goal": NSNull(),
                "requested_preset": NSNull(),
                "requested_representation": NSNull(),
                "instruction_supplied": false,
                "resolved": NSNull(),
            ]
            payload["incompatibilities"] = [[
                "code": "selection-required",
                "fields": ["goal", "preset"],
                "message": "Select a goal and preset.",
            ]]
        }
        let report = try JSONDecoder().decode(CompilePreflight.self, from: data)

        XCTAssertFalse(report.admitted)
        XCTAssertEqual(report.evaluatedThrough, .selection)
        XCTAssertNil(report.selection.resolved)
        XCTAssertNil(report.selection.requestedGoal)
        XCTAssertEqual(report.incompatibilities.first?.code, .selectionRequired)
    }

    func testPreflightArgumentsProjectEveryOverrideExactly() {
        let request = CompilePreflightRequest(
            sources: [URL(fileURLWithPath: "/raw/a.txt"), URL(fileURLWithPath: "/raw/b.md")],
            sourceRoot: URL(fileURLWithPath: "/raw"),
            goal: "continue-a-passage",
            preset: "continue-a-passage.safe",
            representation: "prompt-and-completion",
            instruction: "Use the supplied opening.",
            rules: "whitespace",
            custom: "custom-rule",
            strategy: "paragraph",
            size: 800,
            overlap: 80,
            splitRatioPPM: 400_000,
            requireReview: false,
            consumerProfile: "aptus-handoff-v1",
            minimumTargetCharacters: 90,
            balanceMode: "primary-source-cap",
            maximumRecordsPerPrimarySource: 12,
            evaluationRatioPPM: 200_000,
            evaluationRequired: false,
            splitSeed: "seed-2",
            reviewPolicy: "none"
        )

        XCTAssertEqual(
            VeriformisCLI.preflightArguments(request),
            [
                "preflight", "/raw/a.txt", "/raw/b.md",
                "--source-root", "/raw",
                "--goal", "continue-a-passage",
                "--preset", "continue-a-passage.safe",
                "--representation", "prompt-and-completion",
                "--instruction", "Use the supplied opening.",
                "--rules", "whitespace",
                "--custom", "custom-rule",
                "--strategy", "paragraph",
                "--size", "800",
                "--overlap", "80",
                "--split-ratio-ppm", "400000",
                "--no-require-review",
                "--consumer-profile", "aptus-handoff-v1",
                "--minimum-target-characters", "90",
                "--balance-mode", "primary-source-cap",
                "--maximum-records-per-primary-source", "12",
                "--evaluation-ratio-ppm", "200000",
                "--allow-empty-evaluation",
                "--split-seed", "seed-2",
                "--review-policy", "none",
            ]
        )
    }

    func testPreflightBridgeAcceptsExitZeroAdmissionAndExitTwoRefusal() async throws {
        for admitted in [true, false] {
            let root = temporaryTestDirectory("preflight-exit-\(admitted)")
            defer { try? FileManager.default.removeItem(at: root) }
            try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
            let executable = root.appendingPathComponent("fake-veriformis")
            let arguments = root.appendingPathComponent("arguments.txt")
            try writeExecutable(
                executable,
                script: """
                #!/bin/sh
                printf '%s\n' "$@" > "\(arguments.path)"
                \(try compilePreflightHeredoc(admitted: admitted))
                exit \(admitted ? 0 : 2)
                """
            )
            let request = compilePreflightRequest(root: root)
            let report = try await VeriformisCLI(
                executableURL: executable,
                prefixArguments: []
            ).preflight(request)

            XCTAssertEqual(report.admitted, admitted)
            XCTAssertEqual(
                Array(try recordedArguments(arguments).prefix(10)),
                [
                    "preflight", request.sources[0].path,
                    "--source-root", request.sourceRoot.path,
                    "--goal", request.goal,
                    "--preset", request.preset,
                    "--representation", request.representation,
                ]
            )
        }
    }

    func testPreflightBridgeRejectsInconsistentExitStatus() async throws {
        for (admitted, exitCode) in [(false, 0), (true, 2)] {
            let root = temporaryTestDirectory("preflight-inconsistent-\(exitCode)")
            defer { try? FileManager.default.removeItem(at: root) }
            try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
            let executable = root.appendingPathComponent("fake-veriformis")
            try writeExecutable(
                executable,
                script: """
                #!/bin/sh
                \(try compilePreflightHeredoc(admitted: admitted))
                exit \(exitCode)
                """
            )
            do {
                _ = try await VeriformisCLI(
                    executableURL: executable,
                    prefixArguments: []
                ).preflight(compilePreflightRequest(root: root))
                XCTFail("expected inconsistent exit refusal")
            } catch {
                XCTAssertEqual(
                    error as? CompilePreflightError,
                    .inconsistentExitStatus(exitCode: Int32(exitCode), admitted: admitted)
                )
            }
        }
    }

    func testPreflightBridgeRejectsMalformedTruncatedAndUnexpectedExit() async throws {
        let root = temporaryTestDirectory("preflight-invalid-transport")
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let executable = root.appendingPathComponent("fake-veriformis")
        let request = compilePreflightRequest(root: root)
        let cli = VeriformisCLI(executableURL: executable, prefixArguments: [])

        try writeExecutable(
            executable,
            script: """
            #!/bin/sh
            printf 'not-json\n'
            exit 0
            """
        )
        do {
            _ = try await cli.preflight(request)
            XCTFail("malformed stdout must be refused")
        } catch let error as CompilePreflightError {
            guard case .invalidPayload = error else {
                return XCTFail("unexpected malformed-response error: \(error)")
            }
        }

        try writeExecutable(
            executable,
            script: """
            #!/bin/sh
            \(try compilePreflightHeredoc())
            exit 0
            """
        )
        do {
            _ = try await cli.preflight(
                request,
                controller: CLIProcessController(maxRetainedOutputBytes: 1_024)
            )
            XCTFail("truncated stdout must be refused")
        } catch {
            XCTAssertEqual(error as? CompilePreflightError, .outputTruncated)
        }

        try writeExecutable(
            executable,
            script: """
            #!/bin/sh
            printf 'internal failure\n' >&2
            exit 1
            """
        )
        do {
            _ = try await cli.preflight(request)
            XCTFail("unexpected exit must be refused")
        } catch let error as CompilePreflightError {
            guard case .commandFailed(let exitCode, let message) = error else {
                return XCTFail("unexpected exit-status error: \(error)")
            }
            XCTAssertEqual(exitCode, 1)
            XCTAssertTrue(message.contains("internal failure"))
        }
    }

    func testPreflightCancellationWinsOverAnyPartialResponse() async throws {
        let root = temporaryTestDirectory("preflight-cancel")
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let executable = root.appendingPathComponent("fake-veriformis")
        let started = root.appendingPathComponent("started")
        try writeExecutable(
            executable,
            script: """
            #!/bin/sh
            : > "\(started.path)"
            \(try compilePreflightHeredoc())
            trap 'exit 0' TERM INT
            while :; do sleep 0.02; done
            """
        )
        let controller = CLIProcessController(terminationGrace: 0.1)
        let task = Task {
            try await VeriformisCLI(
                executableURL: executable,
                prefixArguments: []
            ).preflight(compilePreflightRequest(root: root), controller: controller)
        }
        try await waitForFile(started)
        controller.cancel()

        do {
            _ = try await task.value
            XCTFail("cancelled preflight must not accept stdout")
        } catch is CancellationError {
            // Expected: cancellation wins even if complete JSON raced into stdout.
        }
    }

    @MainActor
    func testWorkbenchPreflightCancelsAndDiscardsStaleResponse() async throws {
        let root = temporaryTestDirectory("preflight-stale")
        defer { try? FileManager.default.removeItem(at: root) }
        let output = root.appendingPathComponent("output", isDirectory: true)
        try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)
        let source = root.appendingPathComponent("source.txt")
        try Data("source text".utf8).write(to: source)
        let executable = root.appendingPathComponent("fake-veriformis")
        let firstStarted = root.appendingPathComponent("first-started")
        try writeExecutable(
            executable,
            script: """
            #!/bin/sh
            if [ ! -e "\(firstStarted.path)" ]; then
              : > "\(firstStarted.path)"
              trap 'exit 0' TERM INT
              while :; do sleep 0.02; done
            fi
            \(try compilePreflightHeredoc())
            exit 0
            """
        )
        let defaults = try isolatedDefaults(output: output)
        defer { defaults.defaults.removePersistentDomain(forName: defaults.name) }
        let workbench = WorkbenchViewModel(
            cli: VeriformisCLI(executableURL: executable, prefixArguments: []),
            defaults: defaults.defaults,
            supportDirectory: root.appendingPathComponent("support")
        )
        try configureForPreflight(workbench, source: source, root: root, output: output)

        workbench.refreshCompilePreflight()
        try await waitForFile(firstStarted)
        workbench.splitRatioPPM = 400_000
        XCTAssertEqual(workbench.compilePreflightState, .idle)
        workbench.refreshCompilePreflight()
        let state = try await waitForTerminalPreflightState(workbench)
        guard case .ready(let report) = state else {
            return XCTFail("replacement request did not win: \(state)")
        }
        XCTAssertTrue(report.admitted)
        XCTAssertTrue(workbench.canCompile)
    }

    @MainActor
    func testCompileRerunsPreflightAndCreatesNoWorkspaceWhenSnapshotIsBlocked() async throws {
        let root = temporaryTestDirectory("preflight-jit-block")
        defer { try? FileManager.default.removeItem(at: root) }
        let output = root.appendingPathComponent("output", isDirectory: true)
        try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)
        let source = root.appendingPathComponent("source.txt")
        try Data("source text".utf8).write(to: source)
        let admitted = root.appendingPathComponent("admitted.json")
        let blocked = root.appendingPathComponent("blocked.json")
        try compilePreflightData().write(to: admitted)
        try compilePreflightData(admitted: false).write(to: blocked)
        let executable = root.appendingPathComponent("fake-veriformis")
        let first = root.appendingPathComponent("first")
        try writeExecutable(
            executable,
            script: """
            #!/bin/sh
            if [ ! -e "\(first.path)" ]; then
              : > "\(first.path)"
              cat "\(admitted.path)"
              exit 0
            fi
            cat "\(blocked.path)"
            exit 2
            """
        )
        let defaults = try isolatedDefaults(output: output)
        defer { defaults.defaults.removePersistentDomain(forName: defaults.name) }
        let workbench = WorkbenchViewModel(
            cli: VeriformisCLI(executableURL: executable, prefixArguments: []),
            defaults: defaults.defaults,
            supportDirectory: root.appendingPathComponent("support")
        )
        try configureForPreflight(workbench, source: source, root: root, output: output)

        workbench.refreshCompilePreflight()
        guard case .ready(let firstReport) = try await waitForTerminalPreflightState(workbench) else {
            return XCTFail("initial preflight did not finish")
        }
        XCTAssertTrue(firstReport.admitted)
        XCTAssertTrue(workbench.canCompile)
        workbench.compile()
        try await waitForCompileToFinish(workbench)

        guard case .ready(let finalReport) = workbench.compilePreflightState else {
            return XCTFail("just-in-time preflight report was not retained")
        }
        XCTAssertFalse(finalReport.admitted)
        XCTAssertFalse(workbench.showRunSheet)
        XCTAssertTrue(workbench.runHistory.isEmpty)
        XCTAssertTrue(try FileManager.default.contentsOfDirectory(atPath: output.path).isEmpty)
    }

    @MainActor
    func testCompileCancellationDuringPreflightCreatesNoWorkspaceOrHistory() async throws {
        let root = temporaryTestDirectory("preflight-jit-cancel")
        defer { try? FileManager.default.removeItem(at: root) }
        let output = root.appendingPathComponent("output", isDirectory: true)
        try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)
        let source = root.appendingPathComponent("source.txt")
        try Data("source text".utf8).write(to: source)
        let executable = root.appendingPathComponent("fake-veriformis")
        let started = root.appendingPathComponent("started")
        try writeExecutable(
            executable,
            script: """
            #!/bin/sh
            : > "\(started.path)"
            trap 'exit 0' TERM INT
            while :; do sleep 0.02; done
            """
        )
        let defaults = try isolatedDefaults(output: output)
        defer { defaults.defaults.removePersistentDomain(forName: defaults.name) }
        let workbench = WorkbenchViewModel(
            cli: VeriformisCLI(executableURL: executable, prefixArguments: []),
            defaults: defaults.defaults,
            supportDirectory: root.appendingPathComponent("support")
        )
        try configureForPreflight(workbench, source: source, root: root, output: output)

        workbench.compile()
        try await waitForFile(started)
        XCTAssertFalse(workbench.showRunSheet)
        workbench.cancelCompile()
        try await waitForCompileToFinish(workbench)

        XCTAssertNil(workbench.lastCancellation)
        XCTAssertTrue(workbench.runHistory.isEmpty)
        XCTAssertEqual(workbench.compilePreflightState, .idle)
        XCTAssertTrue(try FileManager.default.contentsOfDirectory(atPath: output.path).isEmpty)
    }

    // MARK: - Goal acceptance matrix (Phase 6.6)

    func testGoalAcceptanceMatrixStrictlyDecodesEveryCellAndProjectsExactCompilePlan() throws {
        let fixture = try goalAcceptanceMatrixFixture()
        XCTAssertEqual(fixture.schemaID, "veriformis.goal-acceptance-matrix/v1")
        XCTAssertEqual(fixture.sourceFixtures.count, 16)
        XCTAssertEqual(fixture.cells.count, 74)

        let goalData = try goalCatalogData()
        let presetData = try recipePresetsData()
        XCTAssertEqual(fixture.catalogSHA256, sha256Hex(goalData))
        XCTAssertEqual(fixture.presetCatalogSHA256, sha256Hex(presetData))
        let goals = try JSONDecoder().decode(GoalCatalog.self, from: goalData)
        let presets = try JSONDecoder().decode(RecipePresetCatalog.self, from: presetData)

        let expectedCellIDs = goals.goals.flatMap { goal in
            goal.eligibleInputFamilies.flatMap { family in
                goal.compatibleRepresentations.map { representation in
                    "\(goal.goalID)__\(family)__\(representation)"
                }
            }
        }
        XCTAssertEqual(fixture.cells.map(\.cellID), expectedCellIDs)
        XCTAssertEqual(Set(expectedCellIDs).count, 74)

        var sourcesByID: [String: GoalAcceptanceMatrixFixture.SourceFixture] = [:]
        for sourceFixture in fixture.sourceFixtures {
            XCTAssertNil(
                sourcesByID.updateValue(
                    sourceFixture,
                    forKey: sourceFixture.sourceFixtureID
                ),
                "duplicate source_fixture_id \(sourceFixture.sourceFixtureID)"
            )
        }
        XCTAssertEqual(sourcesByID.count, fixture.sourceFixtures.count)
        var sourceFixtureContainsNFCNonASCII = false
        for sourceFixture in fixture.sourceFixtures {
            let raw = try XCTUnwrap(
                Data(base64Encoded: sourceFixture.rawBase64),
                "invalid raw_base64 for \(sourceFixture.sourceFixtureID)"
            )
            XCTAssertEqual(raw.count, sourceFixture.size, sourceFixture.sourceFixtureID)
            XCTAssertEqual(sha256Hex(raw), sourceFixture.sha256, sourceFixture.sourceFixtureID)
            XCTAssertFalse(sourceFixture.logicalPath.hasPrefix("/"), sourceFixture.sourceFixtureID)
            XCTAssertFalse(
                sourceFixture.logicalPath.split(separator: "/").contains(".."),
                sourceFixture.sourceFixtureID
            )
            if let text = String(data: raw, encoding: .utf8),
               text.unicodeScalars.contains(where: { $0.value > 0x7F }),
               text == text.precomposedStringWithCanonicalMapping
            {
                sourceFixtureContainsNFCNonASCII = true
            }
        }
        XCTAssertTrue(sourceFixtureContainsNFCNonASCII)

        var fixtureHasExclusions = false
        for cell in fixture.cells {
            guard cell.sourceFixtureIDs.count == 2 else {
                XCTFail("\(cell.cellID): expected exactly two source fixtures")
                continue
            }
            let sourceFixtures = try cell.sourceFixtureIDs.map {
                try XCTUnwrap(sourcesByID[$0], "\(cell.cellID):\($0)")
            }
            XCTAssertTrue(
                sourceFixtures.allSatisfy { $0.inputFamily == cell.inputFamily },
                cell.cellID
            )
            XCTAssertEqual(Set(sourceFixtures.map(\.logicalPath)).count, 2, cell.cellID)
            XCTAssertNotEqual(sourceFixtures[0].sha256, sourceFixtures[1].sha256, cell.cellID)
            XCTAssertTrue(cell.evaluationRequired, cell.cellID)
            fixtureHasExclusions = fixtureHasExclusions || !cell.exclusions.isEmpty
            XCTAssertTrue(
                cell.exclusions.allSatisfy {
                    $0.status == "excluded" && $0.reasonCodes == ["exact-duplicate"]
                },
                cell.cellID
            )
            let goal = try XCTUnwrap(goals.goal(withID: cell.goalID), cell.cellID)
            XCTAssertTrue(goal.eligibleInputFamilies.contains(cell.inputFamily), cell.cellID)
            XCTAssertTrue(
                goal.compatibleRepresentations.contains(cell.representationID),
                cell.cellID
            )
            let preset = try XCTUnwrap(presets.preset(withID: cell.presetID), cell.cellID)
            XCTAssertEqual(preset.goalID, cell.goalID, cell.cellID)
            XCTAssertTrue(preset.curation.evaluationRequired, cell.cellID)

            let sourceRoot = URL(fileURLWithPath: "/matrix/sources", isDirectory: true)
            let sources = sourceFixtures.map {
                sourceRoot.appendingPathComponent($0.logicalPath)
            }
            let workspace = URL(fileURLWithPath: "/matrix/workspace", isDirectory: true)
            let bundle = URL(fileURLWithPath: "/matrix/out.vfbundle", isDirectory: true)
            let plan = VeriformisCLI.compilePlan(
                sources: sources,
                sourceRoot: sourceRoot,
                workspace: workspace,
                bundle: bundle,
                goal: cell.goalID,
                preset: cell.presetID,
                allowEmptyEvaluation: false,
                splitRatioPPM: nil,
                representation: cell.representationID,
                instruction: cell.instruction,
                cleaningRules: cell.cleaningRules,
                cleaningCustom: cell.cleaningCustom,
                chunkSize: cell.chunkSize,
                chunkOverlap: cell.chunkOverlap
            )

            var clean = ["clean", workspace.path]
            if !cell.cleaningRules.isEmpty {
                clean += ["--rules", cell.cleaningRules]
            }
            if !cell.cleaningCustom.isEmpty {
                clean += ["--custom", cell.cleaningCustom]
            }
            var chunk = ["chunk", workspace.path, "--preset", cell.presetID]
            if let chunkSize = cell.chunkSize {
                chunk += ["--size", String(chunkSize)]
            }
            if let chunkOverlap = cell.chunkOverlap {
                chunk += ["--overlap", String(chunkOverlap)]
            }
            var construct = ["construct", workspace.path, "--goal", cell.goalID]
            if cell.chunkSize == nil, cell.chunkOverlap == nil {
                construct += ["--preset", cell.presetID]
            }
            construct += ["--representation", cell.representationID]
            var curate = ["curate", workspace.path, "--preset", cell.presetID]
            if let instruction = cell.instruction {
                curate += ["--instruction", instruction]
            }
            XCTAssertEqual(
                plan,
                [
                    StageCommand(
                        stage: .parse,
                        arguments: ["parse"] + sources.map(\.path) + [
                            "-o", workspace.path, "--source-root", sourceRoot.path,
                        ]
                    ),
                    StageCommand(stage: .clean, arguments: clean),
                    StageCommand(stage: .chunk, arguments: chunk),
                    StageCommand(stage: .construct, arguments: construct),
                    StageCommand(stage: .curate, arguments: curate),
                    StageCommand(stage: .split, arguments: ["split", workspace.path]),
                    StageCommand(stage: .format, arguments: ["format", workspace.path]),
                    StageCommand(stage: .validate, arguments: ["validate", workspace.path]),
                    StageCommand(
                        stage: .seal,
                        arguments: ["seal", workspace.path, "-o", bundle.path]
                    ),
                ],
                cell.cellID
            )
            XCTAssertFalse(
                plan.flatMap(\.arguments).contains("--allow-empty-evaluation"),
                cell.cellID
            )
        }
        XCTAssertTrue(fixtureHasExclusions)
    }

    func testGoalAcceptanceMatrixEveryCellSealsAndVerifiesWithRealRepoCLI() async throws {
        continueAfterFailure = false
        let fixture = try goalAcceptanceMatrixFixture()
        let goals = try JSONDecoder().decode(GoalCatalog.self, from: goalCatalogData())
        let sourcesByID = Dictionary(
            fixture.sourceFixtures.map { ($0.sourceFixtureID, $0) },
            uniquingKeysWith: { first, _ in first }
        )

        let repositoryRoot = testRepositoryRoot()
        let repoCLI = repositoryRoot.appendingPathComponent(".venv/bin/veriformis")
        XCTAssertTrue(FileManager.default.isExecutableFile(atPath: repoCLI.path))
        let cli = try VeriformisCLI.resolve(
            repositoryRoot: repositoryRoot,
            environment: ["VERIFORMIS_CLI": repoCLI.path]
        )
        XCTAssertEqual(cli.executableURL.standardizedFileURL, repoCLI.standardizedFileURL)

        let root = temporaryTestDirectory("phase6-goal-matrix-real-cli")
        defer { try? FileManager.default.removeItem(at: root) }
        var runtimeHasExclusions = false
        for cell in fixture.cells {
            guard cell.sourceFixtureIDs.count == 2 else {
                XCTFail("\(cell.cellID): expected exactly two source fixtures")
                continue
            }
            XCTAssertTrue(cell.evaluationRequired, cell.cellID)
            let cellRoot = root.appendingPathComponent(cell.cellID, isDirectory: true)
            let sourceRoot = cellRoot.appendingPathComponent("sources", isDirectory: true)
            let workspace = cellRoot.appendingPathComponent("workspace", isDirectory: true)
            let bundle = cellRoot.appendingPathComponent("out.vfbundle", isDirectory: true)
            var sources: [URL] = []
            for sourceFixtureID in cell.sourceFixtureIDs {
                let sourceFixture = try XCTUnwrap(
                    sourcesByID[sourceFixtureID],
                    "\(cell.cellID):\(sourceFixtureID)"
                )
                let raw = try XCTUnwrap(
                    Data(base64Encoded: sourceFixture.rawBase64),
                    "\(cell.cellID):\(sourceFixtureID)"
                )
                XCTAssertEqual(raw.count, sourceFixture.size, cell.cellID)
                XCTAssertEqual(sha256Hex(raw), sourceFixture.sha256, cell.cellID)
                let source = sourceRoot.appendingPathComponent(sourceFixture.logicalPath)
                try FileManager.default.createDirectory(
                    at: source.deletingLastPathComponent(),
                    withIntermediateDirectories: true
                )
                try raw.write(to: source)
                sources.append(source)
            }

            let plan = VeriformisCLI.compilePlan(
                sources: sources,
                sourceRoot: sourceRoot,
                workspace: workspace,
                bundle: bundle,
                goal: cell.goalID,
                preset: cell.presetID,
                allowEmptyEvaluation: false,
                splitRatioPPM: nil,
                representation: cell.representationID,
                instruction: cell.instruction,
                cleaningRules: cell.cleaningRules,
                cleaningCustom: cell.cleaningCustom,
                chunkSize: cell.chunkSize,
                chunkOverlap: cell.chunkOverlap
            )
            for command in plan {
                _ = try await requireSuccessfulRealCLI(
                    cli,
                    arguments: command.arguments,
                    operation: "\(cell.cellID):\(command.stage.rawValue)"
                )
            }

            for partition in ["train.jsonl", "evaluation.jsonl"] {
                let data = try Data(
                    contentsOf: bundle
                        .appendingPathComponent("data", isDirectory: true)
                        .appendingPathComponent(partition)
                )
                XCTAssertFalse(data.isEmpty, "\(cell.cellID):\(partition)")
                XCTAssertFalse(
                    data.split(separator: 0x0A, omittingEmptySubsequences: true).isEmpty,
                    "\(cell.cellID):\(partition)"
                )
            }
            let manifest = try Data(
                contentsOf: bundle.appendingPathComponent("manifest.json")
            )
            XCTAssertEqual(sha256Hex(manifest), cell.manifestSHA256, cell.cellID)
            let identity = try bundleValidationIdentity(bundle)
            XCTAssertEqual(identity.recipeID, cell.recipeID, cell.cellID)
            XCTAssertEqual(identity.rowSetSHA256, cell.rowSetSHA256, cell.cellID)

            let preview = try await cli.previewGoal(workspace: workspace)
            let catalogGoal = try XCTUnwrap(goals.goal(withID: cell.goalID))
            XCTAssertEqual(preview.recipeID, cell.recipeID, cell.cellID)
            XCTAssertEqual(preview.lossPolicy, cell.lossPolicy, cell.cellID)
            XCTAssertEqual(preview.lossBoundary, cell.lossBoundary, cell.cellID)
            XCTAssertEqual(preview.notThis, catalogGoal.notThis, cell.cellID)
            XCTAssertEqual(preview.nonClaims, catalogGoal.nonClaims, cell.cellID)
            XCTAssertEqual(preview.records.count, 2, cell.cellID)
            let contextRowKeys = preview.records.first?.contextRowKeys ?? []
            let supervisedRowKey = preview.records.first?.supervised.rowKey ?? ""
            XCTAssertTrue(
                preview.records.allSatisfy {
                    $0.contextRowKeys == contextRowKeys
                        && $0.supervised.rowKey == supervisedRowKey
                },
                cell.cellID
            )
            XCTAssertEqual(contextRowKeys, cell.contextRowKeys, cell.cellID)
            XCTAssertEqual(supervisedRowKey, cell.supervisedRowKey, cell.cellID)
            let supervisedValues = try preview.records.map {
                try XCTUnwrap($0.supervisedValue, "\(cell.cellID):\($0.recordID)")
            }
            if cell.goalID == "extract-a-structured-value" {
                for record in preview.records {
                    let context = try XCTUnwrap(
                        record.context,
                        "\(cell.cellID):\(record.recordID): missing structured context"
                    )
                    XCTAssertTrue(
                        context.values.contains {
                            $0.unicodeScalars.contains { $0.value > 0x7F }
                                && $0 == $0.precomposedStringWithCanonicalMapping
                        },
                        "\(cell.cellID): structured context must contain NFC non-ASCII evidence"
                    )
                }
            } else {
                XCTAssertTrue(
                    supervisedValues.allSatisfy {
                        $0.unicodeScalars.contains { $0.value > 0x7F }
                            && $0 == $0.precomposedStringWithCanonicalMapping
                    },
                    "\(cell.cellID): text supervision must exercise NFC non-ASCII scalars"
                )
            }
            XCTAssertEqual(
                try goalPreviewSupervisionSHA256(preview),
                cell.supervisionSHA256,
                cell.cellID
            )
            XCTAssertEqual(preview.omittedExclusionCount, 0, cell.cellID)
            runtimeHasExclusions = runtimeHasExclusions || !preview.exclusions.isEmpty
            XCTAssertTrue(
                preview.exclusions.allSatisfy {
                    $0.status == "excluded" && $0.reasonCodes == ["exact-duplicate"]
                },
                cell.cellID
            )
            XCTAssertEqual(
                preview.exclusions.map {
                    GoalAcceptanceMatrixFixture.Cell.Exclusion(
                        recordID: $0.recordID,
                        status: $0.status,
                        reasonCodes: $0.reasonCodes
                    )
                },
                cell.exclusions,
                cell.cellID
            )

            let verification = try await requireSuccessfulRealCLI(
                cli,
                arguments: [
                    "verify", bundle.path,
                    "--manifest-sha256", cell.manifestSHA256,
                ],
                operation: "\(cell.cellID):verify"
            )
            XCTAssertTrue(
                verification.combinedOutput.contains("external_digest"),
                cell.cellID
            )
            try FileManager.default.removeItem(at: cellRoot)
        }
        XCTAssertTrue(runtimeHasExclusions)
    }

    @MainActor
    func testNonDeveloperGoalWalkthroughPickPreflightCompilePreviewExportWithRealRepoCLI() async throws {
        continueAfterFailure = false
        let fixture = try goalAcceptanceMatrixFixture()
        let cell = try XCTUnwrap(
            fixture.cells.first {
                $0.cellID == "continue-a-passage__plain-text__prompt-and-completion"
            }
        )
        let sourcesByID = Dictionary(
            fixture.sourceFixtures.map { ($0.sourceFixtureID, $0) },
            uniquingKeysWith: { first, _ in first }
        )
        let repositoryRoot = testRepositoryRoot()
        let repoCLI = repositoryRoot.appendingPathComponent(".venv/bin/veriformis")
        XCTAssertTrue(FileManager.default.isExecutableFile(atPath: repoCLI.path))
        let cli = try VeriformisCLI.resolve(
            repositoryRoot: repositoryRoot,
            environment: ["VERIFORMIS_CLI": repoCLI.path]
        )

        let root = temporaryTestDirectory("phase6-nondeveloper-walkthrough")
        let sourceRoot = root.appendingPathComponent("sources", isDirectory: true)
        let output = root.appendingPathComponent("output", isDirectory: true)
        let support = root.appendingPathComponent("support", isDirectory: true)
        let exportDestination = root.appendingPathComponent("split-jsonl", isDirectory: true)
        try FileManager.default.createDirectory(at: sourceRoot, withIntermediateDirectories: true)
        try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }

        var sources: [URL] = []
        for sourceFixtureID in cell.sourceFixtureIDs {
            let sourceFixture = try XCTUnwrap(sourcesByID[sourceFixtureID])
            let raw = try XCTUnwrap(Data(base64Encoded: sourceFixture.rawBase64))
            XCTAssertEqual(raw.count, sourceFixture.size)
            XCTAssertEqual(sha256Hex(raw), sourceFixture.sha256)
            let source = sourceRoot.appendingPathComponent(sourceFixture.logicalPath)
            try FileManager.default.createDirectory(
                at: source.deletingLastPathComponent(),
                withIntermediateDirectories: true
            )
            try raw.write(to: source)
            sources.append(source)
        }

        let isolated = try isolatedDefaults(output: output)
        defer { isolated.defaults.removePersistentDomain(forName: isolated.name) }
        let goals = try JSONDecoder().decode(GoalCatalog.self, from: goalCatalogData())
        let presets = try JSONDecoder().decode(
            RecipePresetCatalog.self,
            from: recipePresetsData()
        )
        let workbench = WorkbenchViewModel(
            cli: cli,
            defaults: isolated.defaults,
            supportDirectory: support
        )
        workbench.applyCatalogs(goals: goals, presets: presets)
        workbench.sourceURLs = sources
        workbench.sourceRootURL = sourceRoot
        workbench.outputDirectoryURL = output

        // Pick a goal in plain language; the catalog supplies its safe preset.
        workbench.selectGoal("continue-a-passage")
        XCTAssertEqual(workbench.selectedGoal?.title, "Continue a passage")
        XCTAssertEqual(workbench.selectedPresetID, "continue-a-passage.safe")

        // Preflight must admit the exact source snapshot before any workspace exists.
        workbench.refreshCompilePreflight()
        guard case .ready(let preflight) = try await waitForTerminalPreflightState(
            workbench,
            attempts: 12_000
        ) else {
            return XCTFail("real CLI preflight did not return a report")
        }
        XCTAssertTrue(preflight.admitted)
        XCTAssertEqual(preflight.selection.resolved?.goalID, "continue-a-passage")
        XCTAssertTrue(try FileManager.default.contentsOfDirectory(atPath: output.path).isEmpty)

        // Compile through the real CLI and await the automatically loaded goal preview.
        workbench.compile()
        try await waitForCompileToFinish(workbench, attempts: 12_000)
        XCTAssertNil(workbench.lastError)
        XCTAssertEqual(workbench.runHistory.first?.status, .succeeded)
        let compileResult = try XCTUnwrap(workbench.lastResult)
        let manifestSHA256 = try XCTUnwrap(compileResult.manifestSHA256)
        XCTAssertTrue(FileManager.default.fileExists(atPath: compileResult.bundleURL.path))
        XCTAssertTrue(
            FileManager.default.fileExists(atPath: compileResult.transportArchiveURL.path)
        )

        guard case .ready(let preview) = try await waitForTerminalGoalPreviewState(
            workbench,
            attempts: 12_000
        ) else {
            return XCTFail("real CLI goal preview did not become ready")
        }
        let selectedGoal = try XCTUnwrap(workbench.selectedGoal)
        XCTAssertEqual(preview.goalID, selectedGoal.goalID)
        XCTAssertEqual(preview.notThis, selectedGoal.notThis)
        XCTAssertEqual(preview.nonClaims, selectedGoal.nonClaims)
        XCTAssertFalse(preview.records.isEmpty)
        XCTAssertTrue(
            preview.records.allSatisfy { $0.supervised.rowKey == "completion" }
        )

        // Export is a separate, typed derivative of the verified bundle. The
        // dry-run plan identity is carried unchanged into no-replace execute.
        let representation = try XCTUnwrap(
            goals.representation(withID: cell.representationID)
        )
        let containerID = "split-jsonl-directory"
        XCTAssertTrue(representation.compatibleGenericExports.contains(containerID))
        let dryRunRequest = try ExportDryRunRequest(
            bundle: compileResult.bundleURL.path,
            containerID: containerID,
            containerVersion: 1,
            sourceTrustPolicy: .requireExternalDigest,
            expectedManifestSHA256: manifestSHA256
        )
        let dryRunResponse = try await workbench.dryRunExport(dryRunRequest)
        XCTAssertEqual(dryRunResponse.status, .ok)
        let dryRun = try XCTUnwrap(dryRunResponse.result)
        XCTAssertEqual(dryRun.plan.rowSchema, "prompt_completion")
        XCTAssertGreaterThan(dryRun.plan.trainRecordCount, 0)
        XCTAssertGreaterThan(dryRun.plan.evaluationRecordCount, 0)

        let executeRequest = try ExportExecuteRequest(
            bundle: compileResult.bundleURL.path,
            containerID: containerID,
            containerVersion: 1,
            sourceTrustPolicy: .requireExternalDigest,
            expectedManifestSHA256: manifestSHA256,
            destinationRoot: exportDestination.path,
            expectedExportPlanID: dryRun.plan.exportPlanID
        )
        let executeResponse = try await workbench.executeExport(executeRequest)
        XCTAssertEqual(executeResponse.status, .ok)
        let execution = try XCTUnwrap(executeResponse.result)
        XCTAssertEqual(execution.plan.exportPlanID, dryRun.plan.exportPlanID)
        XCTAssertEqual(execution.verification.sourceTrustGrade, .externalDigest)
        XCTAssertEqual(execution.verification.rowSchema, "prompt_completion")
        for relativePath in [
            "data/train.jsonl",
            "data/evaluation.jsonl",
            "export-receipt.json",
        ] {
            let file = exportDestination.appendingPathComponent(relativePath)
            XCTAssertTrue(FileManager.default.fileExists(atPath: file.path), relativePath)
            XCTAssertFalse(try Data(contentsOf: file).isEmpty, relativePath)
        }
    }

    // MARK: - Recipe presets (Phase 6.4)

    func testRecipePresetsDecodeFrozenFixtureExactly() throws {
        let catalog = try JSONDecoder().decode(RecipePresetCatalog.self, from: recipePresetsData())
        XCTAssertEqual(catalog.defaults.segmentation, RecipeSegmentationSettings(strategy: "paragraph", size: 1000, overlap: 100))
        XCTAssertEqual(catalog.defaults.construction.splitRatioPPM, 500_000)
        XCTAssertEqual(catalog.defaults.curation.splitSeed, "veriformis-v1")
        XCTAssertEqual(catalog.presets.count, 5)
        let section = try XCTUnwrap(catalog.safePreset(forGoal: "recover-a-section-from-its-heading"))
        XCTAssertEqual(section.segmentation.strategy, "structure")
        XCTAssertEqual(section.representationID, "prompt-and-completion")
        XCTAssertEqual(catalog.presets(forGoal: "learn-the-text").map(\.presetID), ["learn-the-text.safe"])
    }

    func testRecipePresetsRejectDriftAndMissingKeys() throws {
        XCTAssertThrowsError(
            try JSONDecoder().decode(
                RecipePresetCatalog.self,
                from: recipePresetsData { $0.removeValue(forKey: "defaults") }
            )
        ) { error in
            XCTAssertEqual(
                error as? RecipePresetError,
                .invalidKeySet(scope: "presets", missing: ["defaults"], unexpected: [])
            )
        }
        XCTAssertThrowsError(
            try JSONDecoder().decode(
                RecipePresetCatalog.self,
                from: recipePresetsData { payload in
                    var presets = payload["presets"] as! [[String: Any]]
                    var segmentation = presets[0]["segmentation"] as! [String: Any]
                    segmentation["overlap"] = 1000
                    presets[0]["segmentation"] = segmentation
                    payload["presets"] = presets
                }
            )
        ) { error in
            XCTAssertEqual(error as? RecipePresetError, .invalidMetadata("segmentation"))
        }
    }

    func testRecipePresetsRejectEvaluationRatioEndpoints() throws {
        for endpoint in [0, 1_000_000] {
            XCTAssertThrowsError(
                try JSONDecoder().decode(
                    RecipePresetCatalog.self,
                    from: recipePresetsData { payload in
                        var presets = payload["presets"] as! [[String: Any]]
                        var curation = presets[0]["curation"] as! [String: Any]
                        curation["evaluation_ratio_ppm"] = endpoint
                        presets[0]["curation"] = curation
                        payload["presets"] = presets
                    }
                ),
                "evaluation_ratio_ppm=\(endpoint) must be rejected"
            ) { error in
                XCTAssertEqual(error as? RecipePresetError, .invalidMetadata("curation"))
            }
        }
    }

    func testDiscoverPresetsInvokesExactCLIArgument() async throws {
        let root = temporaryTestDirectory("presets-argv")
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let executable = root.appendingPathComponent("fake-veriformis")
        let arguments = root.appendingPathComponent("arguments.txt")
        try writeExecutable(
            executable,
            script: """
            #!/bin/sh
            printf '%s\\n' "$@" > "\(arguments.path)"
            cat "\(recipePresetsFixtureURL().path)"
            """
        )
        let catalog = try await VeriformisCLI(executableURL: executable, prefixArguments: []).discoverPresets()
        XCTAssertEqual(catalog.presets.count, 5)
        XCTAssertEqual(try String(contentsOf: arguments, encoding: .utf8), "presets\n")
    }

    @MainActor
    func testWorkbenchAdoptsFirstGoalAndSafePresetFromCatalogs() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("veriformis-goal-selection-\(UUID().uuidString)")
        let support = root.appendingPathComponent("support", isDirectory: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let suiteName = "veriformis-tests-\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suiteName))
        defer { defaults.removePersistentDomain(forName: suiteName) }
        let workbench = WorkbenchViewModel(defaults: defaults, supportDirectory: support)
        XCTAssertNil(workbench.selectedGoalID)
        let goals = try JSONDecoder().decode(GoalCatalog.self, from: goalCatalogData())
        let presets = try JSONDecoder().decode(RecipePresetCatalog.self, from: recipePresetsData())
        workbench.applyCatalogs(goals: goals, presets: presets)
        XCTAssertEqual(workbench.selectedGoalID, "learn-the-text")
        XCTAssertEqual(workbench.selectedPresetID, "learn-the-text.safe")
        workbench.selectGoal("recover-a-section-from-its-heading")
        XCTAssertEqual(workbench.selectedPresetID, "recover-a-section-from-its-heading.safe")
        XCTAssertEqual(workbench.selectedGoal?.objective, .sectionReconstruction)
        XCTAssertEqual(workbench.selectedPreset?.segmentation.strategy, "structure")
    }

    // MARK: - Goal preview (Phase 6.3)

    func testGoalPreviewDecodesFrozenFixtureExactly() throws {
        let preview = try JSONDecoder().decode(GoalPreview.self, from: goalPreviewData())

        XCTAssertEqual(preview.goalID, "recover-a-section-from-its-heading")
        XCTAssertEqual(preview.objective, .sectionReconstruction)
        XCTAssertEqual(preview.representationID, "conversation")
        XCTAssertEqual(preview.rowSchema, "messages")
        XCTAssertEqual(preview.lossPolicy, "final-assistant-suffix")
        XCTAssertEqual(preview.availableStages, ["construct", "curate"])
        XCTAssertEqual(preview.records.count, 1)
        let record = try XCTUnwrap(preview.records.first)
        XCTAssertNil(record.omissionReason)
        XCTAssertEqual(record.supervised.rowKey, "messages[1].content")
        XCTAssertEqual(record.supervised.start, 0)
        let value = try XCTUnwrap(record.supervisedValue)
        XCTAssertEqual(value.unicodeScalars.count, record.supervised.end)
        XCTAssertFalse(preview.notThis.isEmpty)
        XCTAssertEqual(preview.nonClaims.count, 4)
        XCTAssertEqual(preview.omittedDiagnosticCount, 0)
        XCTAssertEqual(record.target?["section"], value)
        XCTAssertEqual(record.context?["heading"], "Recovered heading")
        XCTAssertEqual(record.curationStatus, "included")
        XCTAssertFalse(record.recoveredSource.isEmpty)
        XCTAssertTrue(record.recoveredSource.allSatisfy { $0.kind == "source_text" && $0.excerpt != nil })
        XCTAssertEqual(preview.counts["included"], 2)
        XCTAssertTrue(preview.exclusions.isEmpty)
    }

    func testGoalPreviewRejectsMissingKeysWrongSchemaAndRenderedRowDrift() throws {
        XCTAssertThrowsError(
            try JSONDecoder().decode(
                GoalPreview.self,
                from: goalPreviewData { $0.removeValue(forKey: "exclusions") }
            )
        ) { error in
            XCTAssertEqual(
                error as? GoalPreviewError,
                .invalidKeySet(scope: "preview", missing: ["exclusions"], unexpected: [])
            )
        }
        XCTAssertThrowsError(
            try JSONDecoder().decode(
                GoalPreview.self,
                from: goalPreviewData { $0["schema_id"] = "veriformis.goal-preview/v2" }
            )
        ) { error in
            XCTAssertEqual(error as? GoalPreviewError, .invalidMetadata("schema_id"))
        }
        XCTAssertThrowsError(
            try JSONDecoder().decode(
                GoalPreview.self,
                from: goalPreviewData { payload in
                    var records = payload["records"] as! [[String: Any]]
                    records[0]["rendered_row"] = NSNull()
                    payload["records"] = records
                }
            )
        ) { error in
            XCTAssertEqual(error as? GoalPreviewError, .invalidMetadata("rendered_row"))
        }
        XCTAssertThrowsError(
            try JSONDecoder().decode(
                GoalPreview.self,
                from: goalPreviewData { payload in
                    var records = payload["records"] as! [[String: Any]]
                    records[0]["loss"] = "everything"
                    payload["records"] = records
                }
            )
        ) { error in
            XCTAssertEqual(
                error as? GoalPreviewError,
                .invalidKeySet(scope: "record", missing: [], unexpected: ["loss"])
            )
        }
    }

    func testPreviewGoalInvokesExactCLIArguments() async throws {
        let root = temporaryTestDirectory("goal-preview-argv")
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let executable = root.appendingPathComponent("fake-veriformis")
        let arguments = root.appendingPathComponent("arguments.txt")
        try writeExecutable(
            executable,
            script: """
            #!/bin/sh
            printf '%s\\n' "$@" > "\(arguments.path)"
            cat "\(goalPreviewFixtureURL().path)"
            """
        )

        let workspace = root.appendingPathComponent("workspace")
        let preview = try await VeriformisCLI(executableURL: executable, prefixArguments: [])
            .previewGoal(workspace: workspace, representation: "conversation")

        XCTAssertEqual(preview.records.count, 1)
        XCTAssertEqual(
            try String(contentsOf: arguments, encoding: .utf8),
            "goal-preview\n\(workspace.path)\n--representation\nconversation\n"
        )
    }

    // MARK: - Goal catalog (Phase 6.1)

    func testGoalCatalogDecodesFrozenFixtureExactly() throws {
        let catalog = try JSONDecoder().decode(GoalCatalog.self, from: goalCatalogData())

        XCTAssertEqual(catalog.schemaID, "veriformis.goal-catalog/v1")
        XCTAssertEqual(catalog.contractID, "veriformis.goal-catalog")
        XCTAssertEqual(catalog.contractVersion, 1)
        XCTAssertEqual(catalog.goals.map(\.objective), TrainingObjective.allCases)
        XCTAssertEqual(
            catalog.goals.map(\.goalID),
            [
                "learn-the-text",
                "continue-a-passage",
                "recover-a-section-from-its-heading",
                "reproduce-a-recorded-change",
                "extract-a-structured-value",
            ]
        )
        XCTAssertEqual(
            catalog.representations.map(\.rowSchema),
            GoalCatalog.rowSchemaOrder
        )
        for goal in catalog.goals {
            XCTAssertTrue(goal.compatibleRepresentations.contains(goal.defaultRepresentation))
            XCTAssertFalse(goal.notThis.isEmpty)
            XCTAssertEqual(goal.nonClaims, GoalCatalog.nonClaimOrder)
            XCTAssertEqual(goal.state, "implemented")
            XCTAssertNotNil(catalog.representation(withID: goal.defaultRepresentation))
            switch goal.objective {
            case .fullText:
                XCTAssertNil(goal.defaultInstruction)
                XCTAssertNil(goal.instructionTaskClaim)
            case .continuation:
                XCTAssertEqual(
                    goal.defaultInstruction,
                    "Continue the passage with its exact source remainder."
                )
                XCTAssertEqual(goal.instructionTaskClaim, .continuation)
            case .sectionReconstruction:
                XCTAssertEqual(
                    goal.defaultInstruction,
                    "Produce the exact source section body for this heading."
                )
                XCTAssertEqual(goal.instructionTaskClaim, .sectionRecovery)
            case .beforeAfterTransformation:
                XCTAssertEqual(
                    goal.defaultInstruction,
                    "Apply the recorded cleaning change to this exact source text."
                )
                XCTAssertEqual(goal.instructionTaskClaim, .recordedChange)
            case .structuredField:
                XCTAssertEqual(
                    goal.defaultInstruction,
                    "Produce the exact structural attribute recorded by this source."
                )
                XCTAssertEqual(goal.instructionTaskClaim, .structuredExtraction)
            }
        }
        let instruction = try XCTUnwrap(catalog.representation(withID: "instruction-and-output"))
        XCTAssertTrue(instruction.requiresOperatorInstruction)
        XCTAssertEqual(instruction.rowSchema, "instruction_output")
        XCTAssertEqual(
            instruction.compatibleGenericExports,
            ["split-jsonl-directory", "json", "constrained-csv"]
        )
        let conversation = try XCTUnwrap(catalog.representation(withID: "conversation"))
        XCTAssertEqual(conversation.compatibleGenericExports, ["split-jsonl-directory", "json"])
        let structural = try XCTUnwrap(catalog.goal(withID: "extract-a-structured-value"))
        XCTAssertEqual(
            structural.eligibleInputFamilies,
            ["source-code", "markdown", "word-document", "html"]
        )
        XCTAssertFalse(structural.eligibleInputFamilies.contains("delimited-table"))
        XCTAssertFalse(structural.eligibleInputFamilies.contains("pdf-text"))
        let recorded = try XCTUnwrap(catalog.goal(withID: "reproduce-a-recorded-change"))
        XCTAssertFalse(recorded.eligibleInputFamilies.contains("source-code"))
        XCTAssertTrue(recorded.requiredEvidenceDiagnostics.contains("source-chunks-unavailable"))
        XCTAssertEqual(structural.curationDefaults.minimumTargetCharacters, 1)
        XCTAssertEqual(structural.curationDefaults.evaluationRatioPPM, 500_000)
        XCTAssertNil(structural.curationDefaults.maximumRecordsPerPrimarySource)
        XCTAssertEqual(structural.reviewPolicyDefault, "none")
        XCTAssertEqual(structural.reviewPolicyOptions, ["none", "required"])
        XCTAssertEqual(structural.nonClaims.count, 4)
        XCTAssertFalse(structural.requiredEvidenceDiagnostics.isEmpty)
        XCTAssertEqual(catalog.goal(withID: "learn-the-text")?.compatibleRepresentations, ["whole-text"])
        XCTAssertNil(catalog.goal(withID: "summarize-the-document"))
    }

    func testGoalDisclosurePresentationIncludesNotThisAndClosedNonClaims() throws {
        let catalog = try JSONDecoder().decode(GoalCatalog.self, from: goalCatalogData())

        for goal in catalog.goals {
            let lines = GoalDisclosureLine.disclosures(
                notThis: goal.notThis,
                nonClaims: goal.nonClaims
            )
            XCTAssertEqual(
                lines.map(\.kind),
                Array(repeating: .notThis, count: goal.notThis.count)
                    + Array(repeating: .nonClaim, count: goal.nonClaims.count)
            )
            XCTAssertEqual(
                lines.map(\.value),
                goal.notThis + GoalCatalog.nonClaimOrder
            )
            XCTAssertEqual(
                lines.map(\.renderedText),
                goal.notThis.map { "Not this: \($0)" }
                    + GoalCatalog.nonClaimOrder.map { "Does not claim: \($0)" }
            )
        }
    }

    func testGoalCatalogRejectsInstructionDefaultAndTaskClaimDrift() throws {
        for field in ["default_instruction", "instruction_task_claim"] {
            XCTAssertThrowsError(
                try JSONDecoder().decode(
                    GoalCatalog.self,
                    from: goalCatalogData { payload in
                        var goals = payload["goals"] as! [[String: Any]]
                        goals[1].removeValue(forKey: field)
                        payload["goals"] = goals
                    }
                )
            ) { error in
                XCTAssertEqual(
                    error as? GoalCatalogError,
                    .invalidKeySet(
                        scope: "goal",
                        missing: [field],
                        unexpected: []
                    )
                )
            }
        }

        for taskClaim in ["section-recovery", "summarization"] {
            XCTAssertThrowsError(
                try JSONDecoder().decode(
                    GoalCatalog.self,
                    from: goalCatalogData { payload in
                        var goals = payload["goals"] as! [[String: Any]]
                        goals[1]["instruction_task_claim"] = taskClaim
                        payload["goals"] = goals
                    }
                ),
                "task claim \(taskClaim) must fail closed"
            )
        }

        XCTAssertThrowsError(
            try JSONDecoder().decode(
                GoalCatalog.self,
                from: goalCatalogData { payload in
                    var goals = payload["goals"] as! [[String: Any]]
                    goals[0]["default_instruction"] = "Use the whole passage."
                    payload["goals"] = goals
                }
            )
        )
        XCTAssertThrowsError(
            try JSONDecoder().decode(
                GoalCatalog.self,
                from: goalCatalogData { payload in
                    var goals = payload["goals"] as! [[String: Any]]
                    goals[1]["default_instruction"] = NSNull()
                    payload["goals"] = goals
                }
            )
        )
        XCTAssertThrowsError(
            try JSONDecoder().decode(
                GoalCatalog.self,
                from: goalCatalogData { payload in
                    var goals = payload["goals"] as! [[String: Any]]
                    goals[1]["default_instruction"] = " Continue the passage."
                    payload["goals"] = goals
                }
            )
        ) { error in
            XCTAssertEqual(
                error as? GoalCatalogError,
                .invalidMetadata("default_instruction")
            )
        }
    }

    func testGoalCatalogRejectsMissingExtraAndWrongMetadata() throws {
        XCTAssertThrowsError(
            try JSONDecoder().decode(
                GoalCatalog.self,
                from: goalCatalogData { $0.removeValue(forKey: "representations") }
            )
        ) { error in
            XCTAssertEqual(
                error as? GoalCatalogError,
                .invalidKeySet(scope: "catalog", missing: ["representations"], unexpected: [])
            )
        }
        XCTAssertThrowsError(
            try JSONDecoder().decode(
                GoalCatalog.self,
                from: goalCatalogData { $0["format"] = "jsonl" }
            )
        ) { error in
            XCTAssertEqual(
                error as? GoalCatalogError,
                .invalidKeySet(scope: "catalog", missing: [], unexpected: ["format"])
            )
        }
        XCTAssertThrowsError(
            try JSONDecoder().decode(
                GoalCatalog.self,
                from: goalCatalogData { $0["schema_id"] = "veriformis.goal-catalog/v2" }
            )
        ) { error in
            XCTAssertEqual(error as? GoalCatalogError, .invalidMetadata("schema_id"))
        }
        XCTAssertThrowsError(
            try JSONDecoder().decode(
                GoalCatalog.self,
                from: goalCatalogData { payload in
                    var goals = payload["goals"] as! [[String: Any]]
                    goals[0]["summary"] = true
                    payload["goals"] = goals
                }
            )
        ) { error in
            XCTAssertEqual(
                error as? GoalCatalogError,
                .invalidKeySet(scope: "goal", missing: [], unexpected: ["summary"])
            )
        }
    }

    func testGoalCatalogRejectsEvaluationRatioEndpoints() throws {
        for endpoint in [0, 1_000_000] {
            XCTAssertThrowsError(
                try JSONDecoder().decode(
                    GoalCatalog.self,
                    from: goalCatalogData { payload in
                        var goals = payload["goals"] as! [[String: Any]]
                        var defaults = goals[0]["curation_defaults"] as! [String: Any]
                        defaults["evaluation_ratio_ppm"] = endpoint
                        goals[0]["curation_defaults"] = defaults
                        payload["goals"] = goals
                    }
                ),
                "evaluation_ratio_ppm=\(endpoint) must be rejected"
            ) { error in
                XCTAssertEqual(
                    error as? GoalCatalogError,
                    .invalidGoals("curation_defaults out of range")
                )
            }
        }
    }

    func testGoalCatalogRejectsDuplicateGoalUnknownObjectiveAndOpenClosure() throws {
        XCTAssertThrowsError(
            try JSONDecoder().decode(
                GoalCatalog.self,
                from: goalCatalogData { payload in
                    var goals = payload["goals"] as! [[String: Any]]
                    goals[1]["goal_id"] = goals[0]["goal_id"]
                    payload["goals"] = goals
                }
            )
        ) { error in
            XCTAssertEqual(error as? GoalCatalogError, .invalidGoals("duplicate goal_id"))
        }
        XCTAssertThrowsError(
            try JSONDecoder().decode(
                GoalCatalog.self,
                from: goalCatalogData { payload in
                    var goals = payload["goals"] as! [[String: Any]]
                    goals[0]["objective"] = "summary"
                    payload["goals"] = goals
                }
            )
        ) { error in
            XCTAssertEqual(error as? GoalCatalogError, .invalidGoals("unknown objective summary"))
        }
        XCTAssertThrowsError(
            try JSONDecoder().decode(
                GoalCatalog.self,
                from: goalCatalogData { payload in
                    var goals = payload["goals"] as! [[String: Any]]
                    goals.removeLast()
                    payload["goals"] = goals
                }
            )
        ) { error in
            XCTAssertEqual(
                error as? GoalCatalogError,
                .invalidGoals("goals must cover every objective exactly once in taxonomy order")
            )
        }
        XCTAssertThrowsError(
            try JSONDecoder().decode(
                GoalCatalog.self,
                from: goalCatalogData { payload in
                    var goals = payload["goals"] as! [[String: Any]]
                    goals[0]["default_representation"] = "conversation"
                    payload["goals"] = goals
                }
            )
        ) { error in
            XCTAssertEqual(
                error as? GoalCatalogError,
                .invalidGoals("goal learn-the-text representations are not closed over the catalog")
            )
        }
        XCTAssertThrowsError(
            try JSONDecoder().decode(
                GoalCatalog.self,
                from: goalCatalogData { payload in
                    var representations = payload["representations"] as! [[String: Any]]
                    representations[3]["row_schema"] = "chat"
                    payload["representations"] = representations
                }
            )
        ) { error in
            XCTAssertEqual(
                error as? GoalCatalogError,
                .invalidRepresentations(
                    "row schemas must be exactly \(GoalCatalog.rowSchemaOrder) in order"
                )
            )
        }
    }

    func testGoalCatalogRejectsInvalidIdentifiersAndControlCharacters() throws {
        XCTAssertThrowsError(
            try JSONDecoder().decode(
                GoalCatalog.self,
                from: goalCatalogData { payload in
                    var goals = payload["goals"] as! [[String: Any]]
                    goals[0]["goal_id"] = "learn the text"
                    payload["goals"] = goals
                }
            )
        ) { error in
            XCTAssertEqual(error as? GoalCatalogError, .invalidGoals("invalid goal_id learn the text"))
        }
        XCTAssertThrowsError(
            try JSONDecoder().decode(
                GoalCatalog.self,
                from: goalCatalogData { payload in
                    var goals = payload["goals"] as! [[String: Any]]
                    goals[0]["title"] = "Learn\nthe text"
                    payload["goals"] = goals
                }
            )
        ) { error in
            XCTAssertEqual(error as? GoalCatalogError, .invalidMetadata("title"))
        }
        XCTAssertThrowsError(
            try JSONDecoder().decode(
                GoalCatalog.self,
                from: goalCatalogData { payload in
                    var goals = payload["goals"] as! [[String: Any]]
                    var defaults = goals[0]["curation_defaults"] as! [String: Any]
                    defaults["shuffle"] = true
                    goals[0]["curation_defaults"] = defaults
                    payload["goals"] = goals
                }
            )
        ) { error in
            XCTAssertEqual(
                error as? GoalCatalogError,
                .invalidKeySet(scope: "curation_defaults", missing: [], unexpected: ["shuffle"])
            )
        }
        XCTAssertThrowsError(
            try JSONDecoder().decode(
                GoalCatalog.self,
                from: goalCatalogData { payload in
                    var goals = payload["goals"] as! [[String: Any]]
                    goals[0]["review_policy_options"] = ["none"]
                    payload["goals"] = goals
                }
            )
        ) { error in
            XCTAssertEqual(error as? GoalCatalogError, .invalidGoals("review policy options drift"))
        }
        XCTAssertTrue(GoalCatalog.isIdentifier("learn-the-text"))
        XCTAssertFalse(GoalCatalog.isIdentifier("Learn-The-Text"))
        XCTAssertFalse(GoalCatalog.isIdentifier("learn--the"))
        XCTAssertFalse(GoalCatalog.isIdentifier("-learn"))
    }

    func testDiscoverGoalsInvokesExactCLIArgument() async throws {
        let root = temporaryTestDirectory("goals-argv")
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let executable = root.appendingPathComponent("fake-veriformis")
        let arguments = root.appendingPathComponent("arguments.txt")
        try writeExecutable(
            executable,
            script: """
            #!/bin/sh
            printf '%s\\n' "$@" > "\(arguments.path)"
            cat "\(goalCatalogFixtureURL().path)"
            """
        )

        let catalog = try await VeriformisCLI(
            executableURL: executable,
            prefixArguments: []
        ).discoverGoals()

        XCTAssertEqual(catalog.goals.count, 5)
        XCTAssertEqual(
            try String(contentsOf: arguments, encoding: .utf8),
            "goals\n"
        )
    }

    func testDiscoverGoalsReportsCommandFailureWithoutFabricatingGoals() async throws {
        let root = temporaryTestDirectory("goals-failure")
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let executable = root.appendingPathComponent("fake-veriformis")
        try writeExecutable(
            executable,
            script: """
            #!/bin/sh
            echo "error[goal-catalog-invalid]: goal catalog bytes are not canonical" >&2
            exit 2
            """
        )

        do {
            _ = try await VeriformisCLI(executableURL: executable, prefixArguments: []).discoverGoals()
            XCTFail("expected failure")
        } catch let error as GoalCatalogError {
            XCTAssertEqual(
                error,
                .commandFailed(
                    exitCode: 2,
                    message: "error[goal-catalog-invalid]: goal catalog bytes are not canonical"
                )
            )
        }
    }

    func testTaxonomyDiscoveryDecodesExactRegistryPayload() throws {
        let discovery = try JSONDecoder().decode(
            TaxonomyDiscovery.self,
            from: taxonomyData()
        )

        XCTAssertEqual(discovery.contractID, "veriformis.taxonomy")
        XCTAssertEqual(discovery.contractVersion, "1")
        XCTAssertEqual(discovery.schemaID, "veriformis.taxonomy/v1")
        XCTAssertEqual(
            discovery.objectives,
            [
                "full_text",
                "continuation",
                "section_reconstruction",
                "before_after_transformation",
                "structured_field",
            ]
        )
        XCTAssertEqual(discovery.semanticRows.first, "text")
        XCTAssertFalse(discovery.trainingFamilies.isEmpty)
        XCTAssertFalse(discovery.physicalContainers.isEmpty)
        XCTAssertFalse(discovery.consumerProfiles.isEmpty)
        XCTAssertFalse(discovery.lossPolicies.isEmpty)
        XCTAssertEqual(discovery.inputFamilies.first, "plain-text")
        XCTAssertEqual(discovery.inputFamilies.count, 8)
        XCTAssertFalse(TaxonomyDiscovery.expectedKeys.contains("format"))
    }

    func testTaxonomyDiscoveryRejectsMissingAndExtraKeys() throws {
        XCTAssertThrowsError(
            try JSONDecoder().decode(
                TaxonomyDiscovery.self,
                from: taxonomyData { payload in
                    payload.removeValue(forKey: "contract_version")
                }
            )
        ) { error in
            XCTAssertEqual(
                error as? TaxonomyDiscoveryError,
                .invalidKeySet(missing: ["contract_version"], unexpected: [])
            )
        }

        XCTAssertThrowsError(
            try JSONDecoder().decode(
                TaxonomyDiscovery.self,
                from: taxonomyData { payload in
                    payload["format"] = ["jsonl"]
                }
            )
        ) { error in
            XCTAssertEqual(
                error as? TaxonomyDiscoveryError,
                .invalidKeySet(missing: [], unexpected: ["format"])
            )
        }
    }

    func testTaxonomyDiscoveryRejectsWrongSchemaEmptyAxisAndWrongObjectives() throws {
        XCTAssertThrowsError(
            try JSONDecoder().decode(
                TaxonomyDiscovery.self,
                from: taxonomyData { $0["schema_id"] = ["veriformis.taxonomy/v2"] }
            )
        ) { error in
            XCTAssertEqual(error as? TaxonomyDiscoveryError, .invalidMetadata("schema_id"))
        }

        XCTAssertThrowsError(
            try JSONDecoder().decode(
                TaxonomyDiscovery.self,
                from: taxonomyData { $0["semantic_row"] = [] }
            )
        ) { error in
            XCTAssertEqual(error as? TaxonomyDiscoveryError, .invalidAxis("semantic_row"))
        }

        XCTAssertThrowsError(
            try JSONDecoder().decode(
                TaxonomyDiscovery.self,
                from: taxonomyData { $0["objective"] = ["full_text", "summary"] }
            )
        ) { error in
            XCTAssertEqual(
                error as? TaxonomyDiscoveryError,
                .invalidObjectives(["full_text", "summary"])
            )
        }
    }

    func testTaxonomyDiscoveryRejectsMalformedPayload() {
        let malformed = Data(#"{"schema_id":"veriformis.taxonomy/v1"}"#.utf8)
        XCTAssertThrowsError(
            try JSONDecoder().decode(TaxonomyDiscovery.self, from: malformed)
        )
    }

    func testDiscoverTaxonomyInvokesExactCLIArgument() async throws {
        let root = temporaryTestDirectory("taxonomy-argv")
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let executable = root.appendingPathComponent("fake-veriformis")
        let arguments = root.appendingPathComponent("arguments.txt")
        try writeExecutable(
            executable,
            script: """
            #!/bin/sh
            printf '%s\\n' "$@" > "\(arguments.path)"
            \(taxonomyHeredoc())
            """
        )

        let discovery = try await VeriformisCLI(
            executableURL: executable,
            prefixArguments: []
        ).discoverTaxonomy()

        XCTAssertEqual(discovery.schemaID, "veriformis.taxonomy/v1")
        XCTAssertEqual(
            try String(contentsOf: arguments, encoding: .utf8),
            "taxonomy\n"
        )
    }

    func testDiscoverTaxonomyRejectsInvalidUTF8WithoutLossyReplacement() async throws {
        let root = temporaryTestDirectory("taxonomy-invalid-utf8")
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let executable = root.appendingPathComponent("fake-veriformis")
        let responseFile = root.appendingPathComponent("taxonomy.json")
        var response = try taxonomyData()
        let identifier = Data("minimal-v1".utf8)
        let identifierRange = try XCTUnwrap(response.range(of: identifier))
        response.replaceSubrange(identifierRange, with: [0xFF])
        try response.write(to: responseFile)
        try writeExecutable(
            executable,
            script: """
            #!/bin/sh
            cat "\(responseFile.path)"
            printf '\\n'
            """
        )

        do {
            _ = try await VeriformisCLI(
                executableURL: executable,
                prefixArguments: []
            ).discoverTaxonomy()
            XCTFail("invalid UTF-8 must not become an accepted replacement character")
        } catch {
            guard case .invalidPayload = error as? TaxonomyDiscoveryError else {
                return XCTFail("unexpected error: \(error)")
            }
        }
    }

    func testExportDiscoveryDecodesStdoutOnlyAndIgnoresStderrNoise() async throws {
        let root = temporaryTestDirectory("export-discovery")
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let executable = root.appendingPathComponent("fake-veriformis")
        try writeExecutable(
            executable,
            script: """
            #!/bin/sh
            printf 'diagnostic that is not JSON\\n' >&2
            printf '%s\\n' '\(exportDiscoveryResponse())'
            """
        )

        let response = try await VeriformisCLI(
            executableURL: executable,
            prefixArguments: []
        ).discoverExports()

        XCTAssertEqual(response.operation, .discover)
        XCTAssertEqual(response.status, .ok)
        XCTAssertEqual(response.result?.schemaVersion, ExportSurfaceSchema.discovery)
        XCTAssertEqual(response.result?.profiles, [])
        XCTAssertNil(response.error)
    }

    func testExportRequestsEncodeCanonicalRefuseOnlyJSON() throws {
        let request = try ExportDryRunRequest(
            bundle: "/tmp/source.vfbundle",
            containerID: "trainer-jsonl",
            containerVersion: 1,
            sourceTrustPolicy: .requireExternalDigest,
            expectedManifestSHA256: digest("a")
        )

        XCTAssertEqual(
            try request.canonicalJSON(),
            "{\"bundle\":\"/tmp/source.vfbundle\",\"consumer_id\":null,\"consumer_profile_version\":null,\"container_id\":\"trainer-jsonl\",\"container_version\":1,\"expected_manifest_sha256\":\"\(digest("a"))\",\"operation\":\"dry_run\",\"overwrite_policy\":\"refuse\",\"schema_version\":\"veriformis.export-surface-request/v1\",\"source_trust_policy\":\"require_external_digest\"}"
        )
        let lowerTrust = try ExportDryRunRequest(
            bundle: "/tmp/source.vfbundle",
            containerID: "trainer-jsonl",
            containerVersion: 1,
            sourceTrustPolicy: .allowSelfConsistent,
            expectedManifestSHA256: nil
        )
        XCTAssertEqual(
            try lowerTrust.canonicalJSON(),
            "{\"bundle\":\"/tmp/source.vfbundle\",\"consumer_id\":null,\"consumer_profile_version\":null,\"container_id\":\"trainer-jsonl\",\"container_version\":1,\"expected_manifest_sha256\":null,\"operation\":\"dry_run\",\"overwrite_policy\":\"refuse\",\"schema_version\":\"veriformis.export-surface-request/v1\",\"source_trust_policy\":\"allow_self_consistent\"}"
        )
        XCTAssertThrowsError(
            try ExportDryRunRequest(
                bundle: "/tmp/source.vfbundle",
                containerID: "trainer-jsonl",
                containerVersion: 1,
                sourceTrustPolicy: .requireExternalDigest,
                expectedManifestSHA256: nil
            )
        )
        XCTAssertThrowsError(
            try ExportDryRunRequest(
                bundle: "/tmp/source.vfbundle",
                containerID: "trainer-jsonl",
                containerVersion: 1,
                consumerID: "trainer",
                consumerProfileVersion: nil,
                sourceTrustPolicy: .allowSelfConsistent,
                expectedManifestSHA256: nil
            )
        )
    }

    func testConfiguredSplitJSONLRequestsEncodeCanonicalV2JSON() throws {
        let options = try SplitJSONLOptions(
            trainPartitionName: "training-data",
            evaluationPartitionName: "held_out",
            includeProvenance: true
        )
        let dryRun = try ExportDryRunRequestV2(
            bundle: "/tmp/source.vfbundle",
            containerID: "split-jsonl-directory",
            containerVersion: 1,
            sourceTrustPolicy: .requireExternalDigest,
            expectedManifestSHA256: digest("a"),
            containerOptions: options
        )
        let expectedOptions = "\"container_options\":{\"evaluation_partition_name\":\"held_out\",\"include_provenance\":true,\"schema_version\":\"veriformis.split-jsonl-options/v1\",\"train_partition_name\":\"training-data\"}"

        XCTAssertEqual(
            try dryRun.canonicalJSON(),
            "{\"bundle\":\"/tmp/source.vfbundle\",\"consumer_id\":null,\"consumer_profile_version\":null,\"container_id\":\"split-jsonl-directory\",\(expectedOptions),\"container_version\":1,\"expected_manifest_sha256\":\"\(digest("a"))\",\"operation\":\"dry_run\",\"overwrite_policy\":\"refuse\",\"schema_version\":\"veriformis.export-surface-request/v2\",\"source_trust_policy\":\"require_external_digest\"}"
        )

        let execute = try ExportExecuteRequestV2(
            bundle: "/tmp/source.vfbundle",
            containerID: "split-jsonl-directory",
            containerVersion: 1,
            sourceTrustPolicy: .requireExternalDigest,
            expectedManifestSHA256: digest("a"),
            destinationRoot: "/tmp/export",
            expectedExportPlanID: "export-plan-v1-\(digest("b"))",
            containerOptions: options
        )
        XCTAssertEqual(
            try execute.canonicalJSON(),
            "{\"bundle\":\"/tmp/source.vfbundle\",\"consumer_id\":null,\"consumer_profile_version\":null,\"container_id\":\"split-jsonl-directory\",\(expectedOptions),\"container_version\":1,\"destination_root\":\"/tmp/export\",\"expected_export_plan_id\":\"export-plan-v1-\(digest("b"))\",\"expected_manifest_sha256\":\"\(digest("a"))\",\"operation\":\"execute\",\"overwrite_policy\":\"refuse\",\"schema_version\":\"veriformis.export-surface-request/v2\",\"source_trust_policy\":\"require_external_digest\"}"
        )

        let verify = try ExportVerifyRequestV2(
            bundle: "/tmp/source.vfbundle",
            containerID: "split-jsonl-directory",
            containerVersion: 1,
            sourceTrustPolicy: .requireExternalDigest,
            expectedManifestSHA256: digest("a"),
            destinationRoot: "/tmp/export",
            expectedExportPlanID: "export-plan-v1-\(digest("b"))",
            containerOptions: options
        )
        XCTAssertEqual(
            try verify.canonicalJSON(),
            "{\"bundle\":\"/tmp/source.vfbundle\",\"consumer_id\":null,\"consumer_profile_version\":null,\"container_id\":\"split-jsonl-directory\",\(expectedOptions),\"container_version\":1,\"destination_root\":\"/tmp/export\",\"expected_export_plan_id\":\"export-plan-v1-\(digest("b"))\",\"expected_manifest_sha256\":\"\(digest("a"))\",\"operation\":\"verify\",\"overwrite_policy\":\"refuse\",\"schema_version\":\"veriformis.export-surface-request/v2\",\"source_trust_policy\":\"require_external_digest\"}"
        )
    }

    func testCanonicalJSONUsesV1SelectionWithoutContainerOptions() throws {
        let request = try ExportDryRunRequest(
            bundle: "/tmp/source.vfbundle",
            containerID: "json",
            containerVersion: 1,
            sourceTrustPolicy: .requireExternalDigest,
            expectedManifestSHA256: digest("a")
        )

        let encoded = try request.canonicalJSON()
        XCTAssertEqual(
            encoded,
            "{\"bundle\":\"/tmp/source.vfbundle\",\"consumer_id\":null,\"consumer_profile_version\":null,\"container_id\":\"json\",\"container_version\":1,\"expected_manifest_sha256\":\"\(digest("a"))\",\"operation\":\"dry_run\",\"overwrite_policy\":\"refuse\",\"schema_version\":\"veriformis.export-surface-request/v1\",\"source_trust_policy\":\"require_external_digest\"}"
        )
        XCTAssertFalse(encoded.contains("container_options"))
    }

    func testConstrainedCSVUsesV1SelectionWithoutContainerOptions() throws {
        let request = try ExportDryRunRequest(
            bundle: "/tmp/source.vfbundle",
            containerID: "constrained-csv",
            containerVersion: 1,
            sourceTrustPolicy: .requireExternalDigest,
            expectedManifestSHA256: digest("a")
        )

        let encoded = try request.canonicalJSON()
        XCTAssertEqual(
            encoded,
            "{\"bundle\":\"/tmp/source.vfbundle\",\"consumer_id\":null,\"consumer_profile_version\":null,\"container_id\":\"constrained-csv\",\"container_version\":1,\"expected_manifest_sha256\":\"\(digest("a"))\",\"operation\":\"dry_run\",\"overwrite_policy\":\"refuse\",\"schema_version\":\"veriformis.export-surface-request/v1\",\"source_trust_policy\":\"require_external_digest\"}"
        )
        XCTAssertFalse(encoded.contains("container_options"))
    }

    func testConfiguredSplitJSONLRequestsRejectUnsafeOrMismatchedOptions() throws {
        XCTAssertThrowsError(
            try SplitJSONLOptions(
                trainPartitionName: "Train",
                evaluationPartitionName: "evaluation",
                includeProvenance: true
            )
        )
        XCTAssertThrowsError(
            try SplitJSONLOptions(
                trainPartitionName: "same",
                evaluationPartitionName: "same",
                includeProvenance: false
            )
        )
        XCTAssertThrowsError(
            try SplitJSONLOptions(
                trainPartitionName: "con",
                evaluationPartitionName: "evaluation",
                includeProvenance: false
            )
        )
        XCTAssertThrowsError(
            try SplitJSONLOptions(
                trainPartitionName: String(repeating: "a", count: 65),
                evaluationPartitionName: "evaluation",
                includeProvenance: false
            )
        )

        let options = try SplitJSONLOptions(
            trainPartitionName: "train",
            evaluationPartitionName: "evaluation",
            includeProvenance: false
        )
        XCTAssertThrowsError(
            try ExportDryRunRequestV2(
                bundle: "/tmp/source.vfbundle",
                containerID: "other-container",
                containerVersion: 1,
                sourceTrustPolicy: .allowSelfConsistent,
                expectedManifestSHA256: nil,
                containerOptions: options
            )
        )
        XCTAssertThrowsError(
            try ExportDryRunRequestV2(
                bundle: "/tmp/source.vfbundle",
                containerID: "split-jsonl-directory",
                containerVersion: 1,
                consumerID: "trainer",
                consumerProfileVersion: 1,
                sourceTrustPolicy: .allowSelfConsistent,
                expectedManifestSHA256: nil,
                containerOptions: options
            )
        )
    }

    func testExportRuntimePathsEnforceUTF8ByteLimit() throws {
        let exactLimit = String(repeating: "é", count: 16 * 1024)
        XCTAssertEqual(exactLimit.utf8.count, 32 * 1024)
        XCTAssertNoThrow(try ExportInspectRequest(destinationRoot: exactLimit))

        let overLimit = exactLimit + "a"
        XCTAssertEqual(overLimit.utf8.count, (32 * 1024) + 1)
        XCTAssertThrowsError(try ExportInspectRequest(destinationRoot: overLimit))
        XCTAssertThrowsError(
            try ExportDryRunRequest(
                bundle: overLimit,
                containerID: "trainer-jsonl",
                containerVersion: 1,
                sourceTrustPolicy: .allowSelfConsistent,
                expectedManifestSHA256: nil
            )
        )
    }

    func testExportMethodsInvokeExactCommandsWithoutForce() async throws {
        let root = temporaryTestDirectory("export-argv")
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let executable = root.appendingPathComponent("fake-veriformis")
        let arguments = root.appendingPathComponent("arguments.txt")
        try writeExecutable(
            executable,
            script: """
            #!/bin/sh
            printf '%s\\n' "$@" > "\(arguments.path)"
            if [ "$1" = "export-verify" ]; then
              operation=verify
            elif [ "$2" = "dry-run" ]; then
              operation=dry_run
            else
              operation="$2"
            fi
            if [ "$operation" = "dry_run" ]; then
              response_schema=veriformis.export-surface-response/v2
            else
              response_schema=veriformis.export-surface-response/v1
            fi
            printf '{"error":{"code":"invalid-data","message":"not registered"},"operation":"%s","result":null,"schema_version":"%s","status":"error"}\\n' "$operation" "$response_schema"
            exit 1
            """
        )
        let cli = VeriformisCLI(executableURL: executable, prefixArguments: [])
        let dryRun = try exportDryRunRequest()
        let inspect = try ExportInspectRequest(destinationRoot: "/tmp/export")
        let execute = try exportExecuteRequest()
        let verify = try exportVerifyRequest()
        let configuredOptions = try SplitJSONLOptions(
            trainPartitionName: "training-data",
            evaluationPartitionName: "held_out",
            includeProvenance: true
        )
        let configuredDryRun = try ExportDryRunRequestV2(
            bundle: "/tmp/source.vfbundle",
            containerID: "split-jsonl-directory",
            containerVersion: 1,
            sourceTrustPolicy: .requireExternalDigest,
            expectedManifestSHA256: digest("a"),
            containerOptions: configuredOptions
        )
        let configuredExecute = try ExportExecuteRequestV2(
            bundle: "/tmp/source.vfbundle",
            containerID: "split-jsonl-directory",
            containerVersion: 1,
            sourceTrustPolicy: .requireExternalDigest,
            expectedManifestSHA256: digest("a"),
            destinationRoot: "/tmp/export",
            expectedExportPlanID: "export-plan-v1-\(digest("b"))",
            containerOptions: configuredOptions
        )
        let configuredVerify = try ExportVerifyRequestV2(
            bundle: "/tmp/source.vfbundle",
            containerID: "split-jsonl-directory",
            containerVersion: 1,
            sourceTrustPolicy: .requireExternalDigest,
            expectedManifestSHA256: digest("a"),
            destinationRoot: "/tmp/export",
            expectedExportPlanID: "export-plan-v1-\(digest("b"))",
            containerOptions: configuredOptions
        )

        let discovery = try await cli.discoverExports()
        XCTAssertEqual(discovery.status, .error)
        XCTAssertEqual(try recordedArguments(arguments), ["export", "discover"])

        let dryRunResponse = try await cli.dryRunExport(dryRun)
        XCTAssertEqual(dryRunResponse.status, .error)
        XCTAssertEqual(dryRunResponse.schemaVersion, ExportSurfaceSchema.responseV2)
        XCTAssertEqual(
            try recordedArguments(arguments),
            ["export", "dry-run", "--request-json", try dryRun.canonicalJSON()]
        )

        let inspectResponse = try await cli.inspectExport(inspect)
        XCTAssertEqual(inspectResponse.status, .error)
        XCTAssertEqual(
            try recordedArguments(arguments),
            ["export", "inspect", "--request-json", try inspect.canonicalJSON()]
        )

        let executeResponse = try await cli.executeExport(execute)
        XCTAssertEqual(executeResponse.status, .error)
        XCTAssertEqual(
            try recordedArguments(arguments),
            ["export", "execute", "--request-json", try execute.canonicalJSON()]
        )

        let verifyResponse = try await cli.verifyExport(verify)
        XCTAssertEqual(verifyResponse.status, .error)
        XCTAssertEqual(
            try recordedArguments(arguments),
            ["export-verify", "--request-json", try verify.canonicalJSON()]
        )

        let configuredDryRunResponse = try await cli.dryRunExport(configuredDryRun)
        XCTAssertEqual(configuredDryRunResponse.status, .error)
        XCTAssertEqual(
            configuredDryRunResponse.schemaVersion,
            ExportSurfaceSchema.responseV2
        )
        XCTAssertEqual(
            try recordedArguments(arguments),
            ["export", "dry-run", "--request-json", try configuredDryRun.canonicalJSON()]
        )

        let configuredExecuteResponse = try await cli.executeExport(configuredExecute)
        XCTAssertEqual(configuredExecuteResponse.status, .error)
        XCTAssertEqual(
            try recordedArguments(arguments),
            ["export", "execute", "--request-json", try configuredExecute.canonicalJSON()]
        )

        let configuredVerifyResponse = try await cli.verifyExport(configuredVerify)
        XCTAssertEqual(configuredVerifyResponse.status, .error)
        XCTAssertEqual(
            try recordedArguments(arguments),
            ["export-verify", "--request-json", try configuredVerify.canonicalJSON()]
        )
        XCTAssertFalse(
            [
                try dryRun.canonicalJSON(),
                try inspect.canonicalJSON(),
                try execute.canonicalJSON(),
                try verify.canonicalJSON(),
                try configuredDryRun.canonicalJSON(),
                try configuredExecute.canonicalJSON(),
                try configuredVerify.canonicalJSON(),
            ].contains { $0.contains("force") }
        )
    }

    @MainActor
    func testWorkbenchExportDelegatesForwardTypedRequestsUnchanged() async throws {
        let root = temporaryTestDirectory("workbench-export-delegates")
        defer { try? FileManager.default.removeItem(at: root) }
        let output = root.appendingPathComponent("output", isDirectory: true)
        try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)
        let executable = root.appendingPathComponent("fake-veriformis")
        let arguments = root.appendingPathComponent("arguments.txt")
        try writeExecutable(
            executable,
            script: """
            #!/bin/sh
            printf '%s\\n' "$@" > "\(arguments.path)"
            if [ "$2" = "dry-run" ]; then
              operation=dry_run
              response_schema=veriformis.export-surface-response/v2
            else
              operation="$2"
              response_schema=veriformis.export-surface-response/v1
            fi
            printf '{"error":{"code":"invalid-data","message":"delegated"},"operation":"%s","result":null,"schema_version":"%s","status":"error"}\\n' "$operation" "$response_schema"
            exit 1
            """
        )
        let isolated = try isolatedDefaults(output: output)
        defer { isolated.defaults.removePersistentDomain(forName: isolated.name) }
        let workbench = WorkbenchViewModel(
            cli: VeriformisCLI(executableURL: executable, prefixArguments: []),
            defaults: isolated.defaults,
            supportDirectory: root.appendingPathComponent("support", isDirectory: true)
        )

        let dryRun = try exportDryRunRequest()
        let dryRunResponse = try await workbench.dryRunExport(
            dryRun,
            controller: CLIProcessController()
        )
        XCTAssertEqual(dryRunResponse.status, .error)
        XCTAssertEqual(
            try recordedArguments(arguments),
            ["export", "dry-run", "--request-json", try dryRun.canonicalJSON()]
        )

        let execute = try exportExecuteRequest()
        let executeResponse = try await workbench.executeExport(
            execute,
            controller: CLIProcessController()
        )
        XCTAssertEqual(executeResponse.status, .error)
        XCTAssertEqual(
            try recordedArguments(arguments),
            ["export", "execute", "--request-json", try execute.canonicalJSON()]
        )
    }

    @MainActor
    func testWorkbenchExportDelegatesFailClosedWhenCLIIsMissing() async throws {
        let root = temporaryTestDirectory("workbench-export-missing-cli")
        defer { try? FileManager.default.removeItem(at: root) }
        let output = root.appendingPathComponent("output", isDirectory: true)
        try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)
        let isolated = try isolatedDefaults(output: output)
        defer { isolated.defaults.removePersistentDomain(forName: isolated.name) }
        let workbench = WorkbenchViewModel(
            cli: nil,
            defaults: isolated.defaults,
            supportDirectory: root.appendingPathComponent("support", isDirectory: true)
        )

        do {
            _ = try await workbench.dryRunExport(try exportDryRunRequest())
            XCTFail("dry-run must require the resolved CLI")
        } catch {
            XCTAssertEqual(error as? WorkbenchError, .missingCLI)
        }
        do {
            _ = try await workbench.executeExport(try exportExecuteRequest())
            XCTFail("execute must require the resolved CLI")
        } catch {
            XCTAssertEqual(error as? WorkbenchError, .missingCLI)
        }
    }

    func testExportResponseRejectsUnexpectedKeysAtEveryDecodedBoundary() throws {
        let payload = """
        {"error":null,"operation":"discover","result":{"profiles":[],"schema_version":"veriformis.export-discovery/v1","unexpected":true},"schema_version":"veriformis.export-surface-response/v1","status":"ok"}
        """
        XCTAssertThrowsError(
            try JSONDecoder().decode(
                ExportSurfaceResponse<ExportDiscovery>.self,
                from: Data(payload.utf8)
            )
        ) { error in
            XCTAssertEqual(
                error as? ExportSurfaceModelError,
                .invalidKeySet(
                    model: "export discovery",
                    missing: [],
                    unexpected: ["unexpected"]
                )
            )
        }
    }

    func testDryRunBridgeDecodesStrictV2PreviewAndPreservesNestedUnicodeScalars() async throws {
        let root = temporaryTestDirectory("export-dry-run-preview")
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let executable = root.appendingPathComponent("fake-veriformis")
        let responseFile = root.appendingPathComponent("response.json")
        try Data(exportDryRunPreviewResponse().utf8).write(to: responseFile)
        try writeExecutable(
            executable,
            script: """
            #!/bin/sh
            cat "\(responseFile.path)"
            printf '\\n'
            """
        )

        let response = try await VeriformisCLI(
            executableURL: executable,
            prefixArguments: []
        ).dryRunExport(try exportDryRunRequest())
        let result = try XCTUnwrap(response.result)

        XCTAssertEqual(response.schemaVersion, ExportSurfaceSchema.responseV2)
        XCTAssertEqual(result.preview.schemaVersion, ExportSurfaceSchema.dryRunPreview)
        XCTAssertEqual(result.preview.exportPlanID, result.plan.exportPlanID)
        XCTAssertEqual(result.preview.containerProfileID, result.plan.containerProfileID)
        XCTAssertEqual(result.preview.rowSetID, result.plan.rowSetID)
        XCTAssertEqual(result.preview.rowSchema, "messages")
        XCTAssertEqual(
            result.preview.destinationTree.files,
            ["evaluation.jsonl", "export-receipt.json", "train.jsonl"]
        )
        XCTAssertEqual(result.preview.destinationTree.directories, [])
        XCTAssertEqual(
            result.preview.sampleRows.map(\.partition),
            [.train, .evaluation]
        )

        let trainPayload = try XCTUnwrap(result.preview.sampleRows[0].payload)
        guard case .array(let turns)? = trainPayload["messages"],
              turns.count == 2,
              case .object(let firstTurn) = turns[0],
              case .string(let content)? = firstTurn["content"]
        else {
            return XCTFail("nested messages payload did not retain its exact shape")
        }
        let expected = "train \0\r\n\u{001B}\u{009B}\u{202E}\u{00E9}e\u{0301}\u{1F600}"
        XCTAssertEqual(
            content.unicodeScalars.map(\.value),
            expected.unicodeScalars.map(\.value)
        )
        XCTAssertNil(result.preview.sampleRows[0].omissionReason)
    }

    func testDryRunPreviewAcceptsExplicitWholePayloadOmissions() throws {
        let samples = "["
            + "{\"omission_reason\":\"exact-payload-exceeds-preview-limit\",\"ordinal\":0,\"partition\":\"train\",\"payload\":null,\"payload_byte_size\":65537,\"payload_sha256\":\"\(digest("d"))\"},"
            + "{\"omission_reason\":\"exact-payload-exceeds-response-budget\",\"ordinal\":0,\"partition\":\"evaluation\",\"payload\":null,\"payload_byte_size\":128,\"payload_sha256\":\"\(digest("e"))\"}"
            + "]"
        let response = try JSONDecoder().decode(
            ExportSurfaceResponse<ExportDryRunResult>.self,
            from: Data(exportDryRunPreviewResponse(sampleRowsJSON: samples).utf8)
        )
        let rows = try XCTUnwrap(response.result?.preview.sampleRows)

        XCTAssertNil(rows[0].payload)
        XCTAssertEqual(rows[0].omissionReason, .previewLimit)
        XCTAssertEqual(rows[0].payloadByteSize, 65_537)
        XCTAssertNil(rows[1].payload)
        XCTAssertEqual(rows[1].omissionReason, .responseBudget)
        XCTAssertEqual(rows[1].payloadByteSize, 128)
    }

    func testDryRunPreviewAcceptsEmptyEvaluationWithOnlyTrainSample() throws {
        let response = try JSONDecoder().decode(
            ExportSurfaceResponse<ExportDryRunResult>.self,
            from: Data(
                exportDryRunPreviewResponse(evaluationRecordCount: 0).utf8
            )
        )
        let result = try XCTUnwrap(response.result)

        XCTAssertEqual(result.plan.evaluationRecordCount, 0)
        XCTAssertEqual(result.plan.totalRecordCount, 1)
        XCTAssertEqual(result.preview.sampleRows.map(\.partition), [.train])
        XCTAssertEqual(
            result.preview.destinationTree.files,
            ["evaluation.jsonl", "export-receipt.json", "train.jsonl"]
        )
    }

    func testDryRunPreviewRejectsEvaluationSampleWhenPlanEvaluationIsEmpty() throws {
        let response = exportDryRunPreviewResponse(
            evaluationRecordCount: 0,
            includeEvaluationSample: true
        )

        XCTAssertThrowsError(
            try JSONDecoder().decode(
                ExportSurfaceResponse<ExportDryRunResult>.self,
                from: Data(response.utf8)
            )
        )
    }

    func testDryRunPreviewRejectsUnknownMissingAndDetachedEvidence() throws {
        let source = Data(exportDryRunPreviewResponse().utf8)

        var unexpected = try XCTUnwrap(
            JSONSerialization.jsonObject(with: source) as? [String: Any]
        )
        var unexpectedResult = try XCTUnwrap(unexpected["result"] as? [String: Any])
        var unexpectedPreview = try XCTUnwrap(
            unexpectedResult["preview"] as? [String: Any]
        )
        unexpectedPreview["unexpected"] = true
        unexpectedResult["preview"] = unexpectedPreview
        unexpected["result"] = unexpectedResult
        XCTAssertThrowsError(
            try decodeDryRunResponseObject(unexpected)
        ) { error in
            XCTAssertEqual(
                error as? ExportSurfaceModelError,
                .invalidKeySet(
                    model: "export dry-run preview",
                    missing: [],
                    unexpected: ["unexpected"]
                )
            )
        }

        var missing = try XCTUnwrap(
            JSONSerialization.jsonObject(with: source) as? [String: Any]
        )
        var missingResult = try XCTUnwrap(missing["result"] as? [String: Any])
        var missingPreview = try XCTUnwrap(missingResult["preview"] as? [String: Any])
        var missingRows = try XCTUnwrap(missingPreview["sample_rows"] as? [[String: Any]])
        missingRows[0].removeValue(forKey: "payload_sha256")
        missingPreview["sample_rows"] = missingRows
        missingResult["preview"] = missingPreview
        missing["result"] = missingResult
        XCTAssertThrowsError(try decodeDryRunResponseObject(missing))

        var detached = try XCTUnwrap(
            JSONSerialization.jsonObject(with: source) as? [String: Any]
        )
        var detachedResult = try XCTUnwrap(detached["result"] as? [String: Any])
        var detachedPreview = try XCTUnwrap(detachedResult["preview"] as? [String: Any])
        detachedPreview["row_set_id"] = "another-row-set"
        detachedResult["preview"] = detachedPreview
        detached["result"] = detachedResult
        XCTAssertThrowsError(try decodeDryRunResponseObject(detached))

        var wrongTree = try XCTUnwrap(
            JSONSerialization.jsonObject(with: source) as? [String: Any]
        )
        var wrongTreeResult = try XCTUnwrap(wrongTree["result"] as? [String: Any])
        var wrongTreePreview = try XCTUnwrap(
            wrongTreeResult["preview"] as? [String: Any]
        )
        wrongTreePreview["destination_tree"] = [
            "directories": [],
            "files": ["train.jsonl"],
        ]
        wrongTreeResult["preview"] = wrongTreePreview
        wrongTree["result"] = wrongTreeResult
        XCTAssertThrowsError(try decodeDryRunResponseObject(wrongTree))
    }

    func testDryRunRequiresResponseV2WhileOtherOperationsRemainV1() throws {
        let dryRunV1 = "{\"error\":{\"code\":\"invalid-data\",\"message\":\"failed\"},\"operation\":\"dry_run\",\"result\":null,\"schema_version\":\"veriformis.export-surface-response/v1\",\"status\":\"error\"}"
        XCTAssertThrowsError(
            try JSONDecoder().decode(
                ExportSurfaceResponse<ExportDryRunResult>.self,
                from: Data(dryRunV1.utf8)
            )
        )

        let dryRunV2 = dryRunV1.replacingOccurrences(
            of: "veriformis.export-surface-response/v1",
            with: "veriformis.export-surface-response/v2"
        )
        XCTAssertNoThrow(
            try JSONDecoder().decode(
                ExportSurfaceResponse<ExportDryRunResult>.self,
                from: Data(dryRunV2.utf8)
            )
        )

        XCTAssertNoThrow(
            try JSONDecoder().decode(
                ExportSurfaceResponse<ExportDiscovery>.self,
                from: Data(exportDiscoveryResponse().utf8)
            )
        )
        let discoveryV2 = exportDiscoveryResponse().replacingOccurrences(
            of: "veriformis.export-surface-response/v1",
            with: "veriformis.export-surface-response/v2"
        )
        XCTAssertThrowsError(
            try JSONDecoder().decode(
                ExportSurfaceResponse<ExportDiscovery>.self,
                from: Data(discoveryV2.utf8)
            )
        )
    }

    func testExportBridgeRejectsTruncatedOutputBeforeDecode() async throws {
        let root = temporaryTestDirectory("export-truncated")
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let executable = root.appendingPathComponent("fake-veriformis")
        try writeExecutable(
            executable,
            script: """
            #!/bin/sh
            i=0
            while [ "$i" -lt 100 ]; do
              printf 'padding-padding-padding-padding-padding-padding-padding-padding\\n'
              i=$((i + 1))
            done
            printf '%s\\n' '\(exportDiscoveryResponse())'
            """
        )

        do {
            _ = try await VeriformisCLI(
                executableURL: executable,
                prefixArguments: []
            ).discoverExports(
                controller: CLIProcessController(maxRetainedOutputBytes: 1_024)
            )
            XCTFail("truncated output must fail closed")
        } catch {
            XCTAssertEqual(
                error as? ExportCLIBridgeError,
                .outputTruncated(operation: .discover)
            )
        }
    }

    func testExportBridgeAcceptsCanonicalStdoutWhenOnlyDiagnosticsTruncate() async throws {
        let root = temporaryTestDirectory("export-stderr-truncated")
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let executable = root.appendingPathComponent("fake-veriformis")
        try writeExecutable(
            executable,
            script: """
            #!/bin/sh
            printf '%s\\n' '\(exportDiscoveryResponse())'
            i=0
            while [ "$i" -lt 100 ]; do
              printf 'diagnostic-diagnostic-diagnostic-diagnostic-diagnostic\\n' >&2
              i=$((i + 1))
            done
            """
        )

        let response = try await VeriformisCLI(
            executableURL: executable,
            prefixArguments: []
        ).discoverExports(
            controller: CLIProcessController(maxRetainedOutputBytes: 1_024)
        )
        XCTAssertEqual(response.status, .ok)
    }

    func testExportBridgeAcceptsCompleteOKResponseAfterForcedCancellation() async throws {
        let root = temporaryTestDirectory("export-ok-then-killed")
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let executable = root.appendingPathComponent("fake-veriformis")
        let ready = root.appendingPathComponent("ready")
        try writeExecutable(
            executable,
            script: """
            #!/bin/sh
            trap '' TERM
            printf '%s\\n' '\(exportDiscoveryResponse())'
            : > "\(ready.path)"
            while :; do :; done
            """
        )
        let controller = CLIProcessController(terminationGrace: 0.05)
        let task = Task {
            try await VeriformisCLI(
                executableURL: executable,
                prefixArguments: []
            ).discoverExports(controller: controller)
        }
        try await waitForFile(ready)
        controller.cancel()

        let response = try await task.value
        XCTAssertEqual(response.status, .ok)
        XCTAssertEqual(response.result?.profiles, [])
    }

    func testExportBridgeAcceptsVisiblePartialResponseAfterForcedCancellation() async throws {
        let root = temporaryTestDirectory("export-partial-then-killed")
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let executable = root.appendingPathComponent("fake-veriformis")
        let responseFile = root.appendingPathComponent("response.json")
        let ready = root.appendingPathComponent("ready")
        try Data(exportVisiblePartialResponse().utf8).write(to: responseFile)
        try writeExecutable(
            executable,
            script: """
            #!/bin/sh
            trap '' TERM
            cat "\(responseFile.path)"
            printf '\\n'
            : > "\(ready.path)"
            while :; do :; done
            """
        )
        let controller = CLIProcessController(terminationGrace: 0.05)
        let task = Task {
            try await VeriformisCLI(
                executableURL: executable,
                prefixArguments: []
            ).executeExport(
                try exportExecuteRequest(),
                controller: controller
            )
        }
        try await waitForFile(ready)
        controller.cancel()

        let response = try await task.value
        XCTAssertEqual(response.status, .visiblePartial)
        XCTAssertNotNil(response.result)
        XCTAssertEqual(response.error?.code, "export-partial-publication")
    }

    func testExportBridgeRejectsPreprintedErrorAfterForcedCancellationAsAmbiguous() async throws {
        let root = temporaryTestDirectory("export-error-then-killed")
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let executable = root.appendingPathComponent("fake-veriformis")
        let ready = root.appendingPathComponent("ready")
        try writeExecutable(
            executable,
            script: """
            #!/bin/sh
            trap '' TERM
            printf '%s\\n' '{"error":{"code":"invalid-data","message":"preprinted"},"operation":"execute","result":null,"schema_version":"veriformis.export-surface-response/v1","status":"error"}'
            : > "\(ready.path)"
            while :; do :; done
            """
        )
        let controller = CLIProcessController(terminationGrace: 0.05)
        let task = Task {
            try await VeriformisCLI(
                executableURL: executable,
                prefixArguments: []
            ).executeExport(
                try exportExecuteRequest(),
                controller: controller
            )
        }
        try await waitForFile(ready)
        controller.cancel()

        do {
            _ = try await task.value
            XCTFail("a preprinted error does not close state after SIGKILL")
        } catch {
            XCTAssertEqual(
                error as? ExportCLIBridgeError,
                .forcedTermination(operation: .execute)
            )
        }
    }

    func testExportBridgeRejectsForcedKillWithoutCompleteResponseAsAmbiguous() async throws {
        let root = temporaryTestDirectory("export-killed")
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let executable = root.appendingPathComponent("fake-veriformis")
        let ready = root.appendingPathComponent("ready")
        try writeExecutable(
            executable,
            script: """
            #!/bin/sh
            trap '' TERM
            : > "\(ready.path)"
            while :; do :; done
            """
        )
        let controller = CLIProcessController(terminationGrace: 0.05)
        let task = Task {
            try await VeriformisCLI(
                executableURL: executable,
                prefixArguments: []
            ).executeExport(
                try exportExecuteRequest(),
                controller: controller
            )
        }
        try await waitForFile(ready)
        controller.cancel()

        do {
            _ = try await task.value
            XCTFail("force-killed publication must remain ambiguous")
        } catch {
            XCTAssertEqual(
                error as? ExportCLIBridgeError,
                .forcedTermination(operation: .execute)
            )
        }
    }

    func testExportBridgeRejectsNoncanonicalAndDuplicateKeyStdout() async throws {
        let payloads = [
            "{ \"error\": null, \"operation\": \"discover\", \"result\": {\"profiles\":[],\"schema_version\":\"veriformis.export-discovery/v1\"}, \"schema_version\": \"veriformis.export-surface-response/v1\", \"status\": \"ok\" }",
            "{\"error\":null,\"operation\":\"discover\",\"operation\":\"discover\",\"result\":{\"profiles\":[],\"schema_version\":\"veriformis.export-discovery/v1\"},\"schema_version\":\"veriformis.export-surface-response/v1\",\"status\":\"ok\"}",
        ]
        for (index, payload) in payloads.enumerated() {
            let root = temporaryTestDirectory("export-noncanonical-\(index)")
            defer { try? FileManager.default.removeItem(at: root) }
            try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
            let executable = root.appendingPathComponent("fake-veriformis")
            let responseFile = root.appendingPathComponent("response.json")
            try Data(payload.utf8).write(to: responseFile)
            try writeExecutable(
                executable,
                script: """
                #!/bin/sh
                cat "\(responseFile.path)"
                printf '\\n'
                """
            )

            do {
                _ = try await VeriformisCLI(
                    executableURL: executable,
                    prefixArguments: []
                ).discoverExports()
                XCTFail("noncanonical response must be rejected")
            } catch {
                guard case .invalidResponse(operation: .discover, _) = error as? ExportCLIBridgeError else {
                    return XCTFail("unexpected error: \(error)")
                }
            }
        }
    }

    func testDryRunBridgeRejectsNoncanonicalAndDuplicateV2Stdout() async throws {
        let canonical = exportDryRunPreviewResponse()
        let payloads = [
            canonical.replacingOccurrences(
                of: "{\"error\":null",
                with: "{ \"error\":null"
            ),
            canonical.replacingOccurrences(
                of: "\"operation\":\"dry_run\"",
                with: "\"operation\":\"dry_run\",\"operation\":\"dry_run\""
            ),
            canonical.replacingOccurrences(of: "\\u00e9", with: "é"),
            canonical.replacingOccurrences(of: "\\u00e9", with: "\\u00E9"),
        ]
        for (index, payload) in payloads.enumerated() {
            XCTAssertNotEqual(payload, canonical)
            let root = temporaryTestDirectory("export-v2-noncanonical-\(index)")
            defer { try? FileManager.default.removeItem(at: root) }
            try FileManager.default.createDirectory(
                at: root,
                withIntermediateDirectories: true
            )
            let executable = root.appendingPathComponent("fake-veriformis")
            let responseFile = root.appendingPathComponent("response.json")
            try Data(payload.utf8).write(to: responseFile)
            try writeExecutable(
                executable,
                script: """
                #!/bin/sh
                cat "\(responseFile.path)"
                printf '\\n'
                """
            )

            do {
                _ = try await VeriformisCLI(
                    executableURL: executable,
                    prefixArguments: []
                ).dryRunExport(try exportDryRunRequest())
                XCTFail("noncanonical response v2 must be rejected")
            } catch {
                guard case .invalidResponse(operation: .dryRun, _) =
                    error as? ExportCLIBridgeError
                else {
                    return XCTFail("unexpected error: \(error)")
                }
            }
        }
    }

    func testDryRunBridgeRejectsCanonicalV2AbovePreviewResponseLimit() async throws {
        let response = "{"
            + "\"error\":{\"code\":\"invalid-data\",\"message\":\""
            + String(repeating: "x", count: 256 * 1024)
            + "\"},"
            + "\"operation\":\"dry_run\","
            + "\"result\":null,"
            + "\"schema_version\":\"veriformis.export-surface-response/v2\","
            + "\"status\":\"error\""
            + "}"
        let responseData = Data(response.utf8)
        XCTAssertGreaterThan(responseData.count, 256 * 1024)
        XCTAssertLessThan(responseData.count, 1024 * 1024)

        let root = temporaryTestDirectory("export-v2-oversize")
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(
            at: root,
            withIntermediateDirectories: true
        )
        let executable = root.appendingPathComponent("fake-veriformis")
        let responseFile = root.appendingPathComponent("response.json")
        try responseData.write(to: responseFile)
        try writeExecutable(
            executable,
            script: """
            #!/bin/sh
            cat "\(responseFile.path)"
            printf '\\n'
            exit 1
            """
        )

        do {
            _ = try await VeriformisCLI(
                executableURL: executable,
                prefixArguments: []
            ).dryRunExport(try exportDryRunRequest())
            XCTFail("dry-run response v2 above 256 KiB must be rejected")
        } catch {
            guard case .invalidResponse(operation: .dryRun, _) =
                error as? ExportCLIBridgeError
            else {
                return XCTFail("unexpected error: \(error)")
            }
        }
    }

    func testExportBridgeRejectsInvalidUTF8WithoutLossyReplacement() async throws {
        let root = temporaryTestDirectory("export-invalid-utf8")
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let executable = root.appendingPathComponent("fake-veriformis")
        let responseFile = root.appendingPathComponent("response.json")
        var response = Data(
            "{\"error\":{\"code\":\"invalid-data\",\"message\":\"".utf8
        )
        response.append(0xFF)
        response.append(contentsOf: Data(
            "\"},\"operation\":\"discover\",\"result\":null,\"schema_version\":\"veriformis.export-surface-response/v1\",\"status\":\"error\"}".utf8
        ))
        try response.write(to: responseFile)
        try writeExecutable(
            executable,
            script: """
            #!/bin/sh
            cat "\(responseFile.path)"
            printf '\\n'
            exit 1
            """
        )

        do {
            _ = try await VeriformisCLI(
                executableURL: executable,
                prefixArguments: []
            ).discoverExports()
            XCTFail("invalid UTF-8 must not become an accepted replacement character")
        } catch {
            guard case .invalidResponse(operation: .discover, _) = error as? ExportCLIBridgeError else {
                return XCTFail("unexpected error: \(error)")
            }
        }
    }

    func testExportBridgeDecodesSharedFrozenSuccessfulEvidence() async throws {
        let fixture = try exportSurfaceParityFixture()
        let root = temporaryTestDirectory("export-parity")
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let executable = root.appendingPathComponent("fake-veriformis")
        let responseFile = root.appendingPathComponent("response.json")
        try Data(exportSuccessfulExecutionResponse(fixture).utf8).write(to: responseFile)
        try writeExecutable(
            executable,
            script: """
            #!/bin/sh
            cat "\(responseFile.path)"
            printf '\\n'
            """
        )
        let request = try ExportExecuteRequest(
            bundle: "/tmp/source.vfbundle",
            containerID: "trainer-jsonl",
            containerVersion: 1,
            sourceTrustPolicy: .requireExternalDigest,
            expectedManifestSHA256: fixture.sourceManifestSHA256,
            destinationRoot: "/tmp/export",
            expectedExportPlanID: fixture.exact.exportPlanID
        )

        let response = try await VeriformisCLI(
            executableURL: executable,
            prefixArguments: []
        ).executeExport(request)
        let result = try XCTUnwrap(response.result)
        XCTAssertEqual(response.status, .ok)
        XCTAssertEqual(result.plan.exportPlanID, fixture.exact.exportPlanID)
        XCTAssertEqual(result.plan.canonicalSHA256, fixture.exact.planCanonicalSHA256)
        XCTAssertEqual(result.plan.sourceManifestSHA256, fixture.sourceManifestSHA256)
        XCTAssertEqual(result.receipt.exportReceiptID, fixture.exact.exportReceiptID)
        XCTAssertEqual(
            result.receipt.canonicalSHA256,
            fixture.exact.receiptCanonicalSHA256
        )
        XCTAssertEqual(
            result.verification.exportVerificationID,
            fixture.exact.exportVerificationID
        )
        XCTAssertEqual(
            result.verification.canonicalSHA256,
            fixture.exact.verificationCanonicalSHA256
        )
    }

    @MainActor
    func testWorkbenchTaxonomyHelpBecomesReadyWithoutBlocking() async throws {
        let root = temporaryTestDirectory("taxonomy-ready")
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let executable = root.appendingPathComponent("fake-veriformis")
        try writeExecutable(
            executable,
            script: """
            #!/bin/sh
            \(taxonomyHeredoc())
            """
        )
        let suiteName = "veriformis-tests-\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suiteName))
        defer { defaults.removePersistentDomain(forName: suiteName) }
        let workbench = WorkbenchViewModel(
            cli: VeriformisCLI(executableURL: executable, prefixArguments: []),
            defaults: defaults,
            supportDirectory: root.appendingPathComponent("support")
        )

        workbench.refreshTaxonomyHelp()
        XCTAssertEqual(workbench.taxonomyHelpState, .loading)
        let state = try await waitForTerminalTaxonomyState(workbench)
        guard case .ready(let discovery) = state else {
            return XCTFail("expected ready taxonomy state, observed \(state)")
        }
        XCTAssertEqual(discovery.consumerProfiles.last, "aptus-handoff-v1")
    }

    @MainActor
    func testWorkbenchTaxonomyHelpReportsUnavailablePayload() async throws {
        let root = temporaryTestDirectory("taxonomy-unavailable")
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let executable = root.appendingPathComponent("fake-veriformis")
        try writeExecutable(
            executable,
            script: """
            #!/bin/sh
            printf 'not-json\\n'
            """
        )
        let suiteName = "veriformis-tests-\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suiteName))
        defer { defaults.removePersistentDomain(forName: suiteName) }
        let workbench = WorkbenchViewModel(
            cli: VeriformisCLI(executableURL: executable, prefixArguments: []),
            defaults: defaults,
            supportDirectory: root.appendingPathComponent("support")
        )

        workbench.refreshTaxonomyHelp()
        let state = try await waitForTerminalTaxonomyState(workbench)
        guard case .unavailable(let message) = state else {
            return XCTFail("expected unavailable taxonomy state, observed \(state)")
        }
        XCTAssertTrue(message.contains("invalid JSON"), message)
    }

    @MainActor
    func testWorkbenchTaxonomyHelpCancelsAndReplacesStaleRequest() async throws {
        let root = temporaryTestDirectory("taxonomy-replace")
        defer { try? FileManager.default.removeItem(at: root) }
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let executable = root.appendingPathComponent("fake-veriformis")
        let firstStarted = root.appendingPathComponent("first-started")
        try writeExecutable(
            executable,
            script: """
            #!/bin/sh
            if [ ! -e "\(firstStarted.path)" ]; then
              : > "\(firstStarted.path)"
              trap 'exit 0' TERM INT
              while :; do :; done
            fi
            \(taxonomyHeredoc())
            """
        )
        let suiteName = "veriformis-tests-\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suiteName))
        defer { defaults.removePersistentDomain(forName: suiteName) }
        let workbench = WorkbenchViewModel(
            cli: VeriformisCLI(executableURL: executable, prefixArguments: []),
            defaults: defaults,
            supportDirectory: root.appendingPathComponent("support")
        )

        workbench.refreshTaxonomyHelp()
        for _ in 0 ..< 100 where !FileManager.default.fileExists(atPath: firstStarted.path) {
            try await Task.sleep(nanoseconds: 10_000_000)
        }
        XCTAssertTrue(FileManager.default.fileExists(atPath: firstStarted.path))

        workbench.refreshTaxonomyHelp()
        let state = try await waitForTerminalTaxonomyState(workbench)
        guard case .ready(let discovery) = state else {
            return XCTFail("replacement request did not win: \(state)")
        }
        XCTAssertEqual(discovery.contractID, "veriformis.taxonomy")
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
            goal: "continue-a-passage",
            preset: "continue-a-passage.safe",
            allowEmptyEvaluation: true,
            splitRatioPPM: 400_000,
            includeHandoff: true
        )

        XCTAssertEqual(plan.map(\.stage), [
            .parse, .clean, .chunk, .construct, .curate, .split, .format, .validate, .seal,
        ])
        XCTAssertEqual(plan[0].arguments.first, "parse")
        XCTAssertTrue(plan[0].arguments.contains("--source-root"))
        XCTAssertEqual(plan[2].arguments, ["chunk", workspace.path, "--preset", "continue-a-passage.safe"])
        XCTAssertEqual(
            plan[3].arguments,
            [
                "construct", workspace.path, "--goal", "continue-a-passage",
                "--preset", "continue-a-passage.safe",
                "--consumer-profile", "aptus-handoff-v1",
                "--split-ratio-ppm", "400000",
            ]
        )
        XCTAssertEqual(plan[4].arguments.prefix(4), ["curate", workspace.path, "--preset", "continue-a-passage.safe"])
        XCTAssertTrue(plan[4].arguments.contains("--allow-empty-evaluation"))
        XCTAssertEqual(plan[6].stage.rawValue, "format")
        XCTAssertEqual(plan[6].arguments, ["format", workspace.path])
        XCTAssertEqual(
            plan[8].arguments,
            ["seal", workspace.path, "-o", bundle.path, "--aptus-handoff"]
        )
    }

    func testCompilePlanProjectsPhase66MatrixBridgeOverridesExactly() throws {
        let workspace = URL(fileURLWithPath: "/tmp/ws")
        let plan = VeriformisCLI.compilePlan(
            sources: [URL(fileURLWithPath: "/data/raw/a.txt")],
            sourceRoot: URL(fileURLWithPath: "/data/raw"),
            workspace: workspace,
            bundle: URL(fileURLWithPath: "/tmp/out.vfbundle"),
            goal: "continue-a-passage",
            preset: "continue-a-passage.safe",
            allowEmptyEvaluation: false,
            splitRatioPPM: nil,
            representation: "instruction-and-output",
            instruction: "Continue the supplied passage.",
            cleaningRules: "whitespace,urls",
            cleaningCustom: "strip_margin"
        )

        XCTAssertEqual(
            try XCTUnwrap(plan.first { $0.stage == .clean }).arguments,
            ["clean", workspace.path, "--rules", "whitespace,urls", "--custom", "strip_margin"]
        )
        XCTAssertEqual(
            try XCTUnwrap(plan.first { $0.stage == .construct }).arguments,
            [
                "construct", workspace.path,
                "--goal", "continue-a-passage",
                "--preset", "continue-a-passage.safe",
                "--representation", "instruction-and-output",
            ]
        )
        XCTAssertEqual(
            try XCTUnwrap(plan.first { $0.stage == .curate }).arguments,
            [
                "curate", workspace.path,
                "--preset", "continue-a-passage.safe",
                "--instruction", "Continue the supplied passage.",
            ]
        )
    }

    func testCompilePlanProjectsSegmentationOverridesWithoutReassertingPresetAtConstruct() throws {
        let workspace = URL(fileURLWithPath: "/tmp/ws")
        let plan = VeriformisCLI.compilePlan(
            sources: [URL(fileURLWithPath: "/data/raw/a.txt")],
            sourceRoot: URL(fileURLWithPath: "/data/raw"),
            workspace: workspace,
            bundle: URL(fileURLWithPath: "/tmp/out.vfbundle"),
            goal: "reproduce-a-recorded-change",
            preset: "reproduce-a-recorded-change.safe",
            allowEmptyEvaluation: true,
            splitRatioPPM: nil,
            representation: "prompt-and-completion",
            chunkSize: 24,
            chunkOverlap: 0
        )

        XCTAssertEqual(
            try XCTUnwrap(plan.first { $0.stage == .chunk }).arguments,
            [
                "chunk", workspace.path,
                "--preset", "reproduce-a-recorded-change.safe",
                "--size", "24",
                "--overlap", "0",
            ]
        )
        XCTAssertEqual(
            try XCTUnwrap(plan.first { $0.stage == .construct }).arguments,
            [
                "construct", workspace.path,
                "--goal", "reproduce-a-recorded-change",
                "--representation", "prompt-and-completion",
            ]
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
            goal: "learn-the-text",
            preset: "learn-the-text.safe",
            allowEmptyEvaluation: false,
            splitRatioPPM: nil
        )
        XCTAssertEqual(plan.last!.arguments, ["seal", workspace.path, "-o", bundle.path])
        XCTAssertFalse(
            plan.flatMap(\.arguments).contains { $0.lowercased().contains("aptus") }
        )
    }

    @MainActor
    func testDefaultCompileFailsClosedAndMatchesCLISplitDefault() throws {

        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("veriformis-defaults-\(UUID().uuidString)")
        let output = root.appendingPathComponent("output", isDirectory: true)
        let support = root.appendingPathComponent("support", isDirectory: true)
        try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let suiteName = "veriformis-tests-\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suiteName))
        defaults.set(output.path, forKey: "veriformis.workbench.defaultOutput")
        defer { defaults.removePersistentDomain(forName: suiteName) }

        // A fresh workbench holds no recipe constant: it starts fail-closed and
        // with no split-ratio override, so the CLI preset data supplies both.
        let workbench = WorkbenchViewModel(defaults: defaults, supportDirectory: support)
        XCTAssertFalse(workbench.allowEmptyEvaluation)
        XCTAssertNil(workbench.splitRatioPPM)

        // The default compile plan must never weaken the curate gate…
        let workspace = URL(fileURLWithPath: "/tmp/ws")
        let plan = VeriformisCLI.compilePlan(
            sources: [URL(fileURLWithPath: "/data/a.txt")],
            sourceRoot: URL(fileURLWithPath: "/data"),
            workspace: workspace,
            bundle: URL(fileURLWithPath: "/tmp/out.vfbundle"),
            goal: "continue-a-passage",
            preset: "continue-a-passage.safe",
            allowEmptyEvaluation: workbench.allowEmptyEvaluation,
            splitRatioPPM: workbench.splitRatioPPM
        )
        XCTAssertFalse(
            plan.flatMap(\.arguments).contains("--allow-empty-evaluation"),
            "default GUI compile must match the CLI --require-evaluation default"
        )
        // …and with no override the plan passes no split ratio at all: the
        // CLI's versioned preset data supplies it.
        let construct = try XCTUnwrap(plan.first { $0.stage == .construct })
        XCTAssertFalse(construct.arguments.contains("--split-ratio-ppm"))
        XCTAssertEqual(construct.arguments.prefix(6), ["construct", workspace.path, "--goal", "continue-a-passage", "--preset", "continue-a-passage.safe"])
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
            stage: WorkbenchStage.format.rawValue,
            exitCode: 2,
            message: "boom\nline2"
        )
        let failure = WorkbenchViewModel.makeFailure(
            error: error,
            logLines: ["a", "b", "c"],
            workspace: URL(fileURLWithPath: "/tmp/ws"),
            logFile: nil
        )
        XCTAssertEqual(failure.stage, "format")
        XCTAssertEqual(failure.stageTitle, "Lower rows")
        XCTAssertEqual(failure.exitCode, 2)
        XCTAssertTrue(failure.summary.contains("Stage Lower rows failed"))
        XCTAssertTrue(failure.summary.contains("exit 2"))
        XCTAssertEqual(failure.lastLogLines, ["a", "b", "c"])
        XCTAssertTrue(error.localizedDescription.contains("Stage Lower rows failed"))
    }

    func testPipelineStageCountIsNine() {
        XCTAssertEqual(WorkbenchStage.pipelineStages.count, 9)
        XCTAssertFalse(WorkbenchStage.pipelineStages.contains(.verify))
    }

    func testFormatStageAliasIsDisplayOnlyAndUnknownStagesPassThrough() throws {
        XCTAssertEqual(WorkbenchStage.format.rawValue, "format")
        XCTAssertEqual(WorkbenchStage.format.title, "Lower rows")
        XCTAssertEqual(
            WorkbenchStage.displayTitle(forRawValue: WorkbenchStage.format.rawValue),
            "Lower rows"
        )
        XCTAssertEqual(
            WorkbenchStage.displayTitle(forRawValue: "future_stage"),
            "future_stage"
        )

        let entry = historyEntry(
            writeAptusHandoff: false,
            failedStage: WorkbenchStage.format.rawValue
        )
        let decoded = try JSONDecoder().decode(
            RunHistoryEntry.self,
            from: JSONEncoder().encode(entry)
        )
        XCTAssertEqual(decoded.failedStage, "format")
        XCTAssertEqual(decoded.failedStageTitle, "Lower rows")
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

    private func historyEntry(
        writeAptusHandoff: Bool?,
        failedStage: String? = nil
    ) -> RunHistoryEntry {
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
            goalID: nil,
            presetID: nil,
            failedStage: failedStage,
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

    private func taxonomyPayload() -> [String: [String]] {
        [
            "contract_id": ["veriformis.taxonomy"],
            "contract_version": ["1"],
            "schema_id": ["veriformis.taxonomy/v1"],
            "training_family": [
                "source-grounded-language-modeling",
                "source-grounded-supervised-fine-tuning",
            ],
            "objective": [
                "full_text",
                "continuation",
                "section_reconstruction",
                "before_after_transformation",
                "structured_field",
            ],
            "semantic_row": [
                "text",
                "prompt_completion",
                "instruction_output",
                "messages",
            ],
            "physical_container": [
                "minimal-v1",
                "deterministic-vfbundle-zip-v1",
            ],
            "consumer_profile": [
                "veriformis-canonical-v1",
                "aptus-handoff-v1",
            ],
            "loss_policy": [
                "full-sequence",
                "completion-only",
                "output-only",
                "final-assistant-suffix",
            ],
            "input_family": [
                "plain-text",
                "source-code",
                "markdown",
                "word-document",
                "html",
                "pdf-text",
                "delimited-table",
                "json-records",
            ],
        ]
    }

    private func exportDiscoveryResponse() -> String {
        "{\"error\":null,\"operation\":\"discover\",\"result\":{\"profiles\":[],\"schema_version\":\"veriformis.export-discovery/v1\"},\"schema_version\":\"veriformis.export-surface-response/v1\",\"status\":\"ok\"}"
    }

    private func exportDryRunPreviewResponse(
        sampleRowsJSON: String? = nil,
        evaluationRecordCount: Int = 1,
        includeEvaluationSample: Bool? = nil
    ) -> String {
        precondition(evaluationRecordCount >= 0)
        let source = Data(exportVisiblePartialResponse().utf8)
        let response = try! JSONSerialization.jsonObject(with: source) as! [String: Any]
        let result = response["result"] as! [String: Any]
        var plan = result["plan"] as! [String: Any]
        plan["evaluation_record_count"] = evaluationRecordCount
        plan["row_schema"] = "messages"
        plan["total_record_count"] = 1 + evaluationRecordCount

        let trainFile = (plan["files"] as! [[String: Any]])[0]
        var evaluationFile = trainFile
        evaluationFile["file_plan_id"] = "evaluation-file-plan"
        evaluationFile["membership_scope"] = "evaluation"
        evaluationFile["path"] = "evaluation.jsonl"
        evaluationFile["record_count"] = evaluationRecordCount
        evaluationFile["role"] = "evaluation"
        plan["files"] = [evaluationFile, trainFile]

        let planData = try! JSONSerialization.data(
            withJSONObject: plan,
            options: [.sortedKeys, .withoutEscapingSlashes]
        )
        let planJSON = String(decoding: planData, as: UTF8.self)

        let trainExactUnicode = "\u{009B}\u{202E}\u{00E9}e\u{0301}\u{1F600}"
        let trainCanonicalPayload =
            #"{"messages":[{"content":"train \u0000\r\n\u001b"#
            + trainExactUnicode
            + #"","role":"user"},{"content":"assistant","role":"assistant"}]}"#
        let trainResponsePayload =
            #"{"messages":[{"content":"train \u0000\r\n\u001b\u009b\u202e\u00e9e\u0301\ud83d\ude00","role":"user"},{"content":"assistant","role":"assistant"}]}"#
        let evaluationCanonicalPayload =
            #"{"messages":[{"content":"evaluation","role":"user"},{"content":"assistant","role":"assistant"}]}"#

        let includeEvaluation = includeEvaluationSample
            ?? (evaluationRecordCount > 0)
        var defaultSamples = exportDryRunSampleJSON(
            partition: "train",
            responsePayloadJSON: trainResponsePayload,
            canonicalPayloadJSON: trainCanonicalPayload
        )
        if includeEvaluation {
            defaultSamples += "," + exportDryRunSampleJSON(
                partition: "evaluation",
                responsePayloadJSON: evaluationCanonicalPayload,
                canonicalPayloadJSON: evaluationCanonicalPayload
            )
        }
        let samples = sampleRowsJSON ?? "[\(defaultSamples)]"
        let preview = "{"
            + "\"container_profile_id\":\"container-profile\","
            + "\"destination_tree\":{\"directories\":[],\"files\":[\"evaluation.jsonl\",\"export-receipt.json\",\"train.jsonl\"]},"
            + "\"export_plan_id\":\"plan\","
            + "\"maximum_sample_payload_bytes\":65536,"
            + "\"row_schema\":\"messages\","
            + "\"row_set_id\":\"row-set\","
            + "\"sample_policy\":\"first-row-per-non-empty-partition\","
            + "\"sample_rows\":\(samples),"
            + "\"schema_version\":\"veriformis.export-dry-run-preview/v1\""
            + "}"
        return "{"
            + "\"error\":null,"
            + "\"operation\":\"dry_run\","
            + "\"result\":{\"plan\":\(planJSON),\"preview\":\(preview)},"
            + "\"schema_version\":\"veriformis.export-surface-response/v2\","
            + "\"status\":\"ok\""
            + "}"
    }

    private func exportDryRunSampleJSON(
        partition: String,
        responsePayloadJSON: String,
        canonicalPayloadJSON: String
    ) -> String {
        let payload = Data(canonicalPayloadJSON.utf8)
        let payloadSHA256 = SHA256.hash(data: payload)
            .map { String(format: "%02x", $0) }
            .joined()
        return "{"
            + "\"omission_reason\":null,"
            + "\"ordinal\":0,"
            + "\"partition\":\"\(partition)\","
            + "\"payload\":\(responsePayloadJSON),"
            + "\"payload_byte_size\":\(payload.count),"
            + "\"payload_sha256\":\"\(payloadSHA256)\""
            + "}"
    }

    private func decodeDryRunResponseObject(
        _ value: [String: Any]
    ) throws -> ExportSurfaceResponse<ExportDryRunResult> {
        let data = try JSONSerialization.data(
            withJSONObject: value,
            options: [.sortedKeys, .withoutEscapingSlashes]
        )
        return try JSONDecoder().decode(
            ExportSurfaceResponse<ExportDryRunResult>.self,
            from: data
        )
    }

    private func exportVisiblePartialResponse() -> String {
        let hash = digest("c")
        let plan: [String: Any] = [
            "canonical_sha256": hash,
            "consumer_profile_id": NSNull(),
            "container_profile_id": "container-profile",
            "evaluation_record_count": 0,
            "export_plan_id": "plan",
            "files": [[
                "expected_byte_size": 1,
                "expected_sha256": hash,
                "file_plan_id": "file-plan",
                "media_type": "application/jsonl",
                "membership_scope": "train",
                "path": "train.jsonl",
                "record_count": 1,
                "role": "train",
                "semantic_content_sha256": NSNull(),
            ]],
            "membership_projection_id": "membership",
            "overwrite_policy": "refuse",
            "row_schema": "text",
            "row_set_id": "row-set",
            "source_bundle_id": "bundle",
            "source_manifest_sha256": hash,
            "source_trust_grade": "external_digest",
            "source_trust_policy": "require_external_digest",
            "total_record_count": 1,
            "train_record_count": 1,
        ]
        let destinationFile: [String: Any] = [
            "byte_size": 1,
            "destination_file_id": "destination-file",
            "file_plan_id": "file-plan",
            "media_type": "application/jsonl",
            "membership_scope": "train",
            "path": "train.jsonl",
            "record_count": 1,
            "role": "train",
            "schema_version": "veriformis.export-destination-file-binding/v1",
            "semantic_content_sha256": NSNull(),
            "sha256": hash,
        ]
        let receipt: [String: Any] = [
            "canonical_sha256": hash,
            "export_plan_id": "plan",
            "export_receipt_id": "receipt",
            "files": [destinationFile],
            "output_content_root_sha256": hash,
        ]
        let verification: [String: Any] = [
            "canonical_sha256": hash,
            "consumer_profile_id": NSNull(),
            "container_profile_id": "container-profile",
            "dataset_snapshot_id": "snapshot",
            "declared_record_count": 1,
            "determinism_claim": "portable_exact_bytes",
            "export_plan_id": "plan",
            "export_receipt_id": "receipt",
            "export_verification_id": "verification",
            "membership_projection_id": "membership",
            "output_content_root_sha256": hash,
            "output_file_count": 1,
            "row_schema": "text",
            "row_set_id": "row-set",
            "schema_version": "veriformis.export-verification/v1",
            "source_bundle_id": "bundle",
            "source_content_root_sha256": hash,
            "source_manifest_sha256": hash,
            "source_trust_grade": "external_digest",
            "source_verification_id": "source-verification",
            "split_result_id": "split",
            "validation_report_id": "validation",
        ]
        let payload: [String: Any] = [
            "error": [
                "code": "export-partial-publication",
                "message": "visible publication requires attention",
            ],
            "operation": "execute",
            "result": [
                "destination_root": "/tmp/export",
                "durability_warning": "directory fsync was unavailable",
                "plan": plan,
                "receipt": receipt,
                "verification": verification,
            ],
            "schema_version": "veriformis.export-surface-response/v1",
            "status": "visible_partial",
        ]
        let data = try! JSONSerialization.data(
            withJSONObject: payload,
            options: [.sortedKeys, .withoutEscapingSlashes]
        )
        guard let response = String(bytes: data, encoding: .utf8) else {
            preconditionFailure("JSONSerialization must produce UTF-8 JSON")
        }
        return response
    }

    private func exportSuccessfulExecutionResponse(
        _ fixture: ExportSurfaceParityFixture
    ) -> String {
        let source = Data(exportVisiblePartialResponse().utf8)
        var payload = try! JSONSerialization.jsonObject(with: source) as! [String: Any]
        payload["error"] = NSNull()
        payload["status"] = "ok"

        var result = payload["result"] as! [String: Any]
        result["durability_warning"] = NSNull()
        var plan = result["plan"] as! [String: Any]
        plan["canonical_sha256"] = fixture.exact.planCanonicalSHA256
        plan["export_plan_id"] = fixture.exact.exportPlanID
        plan["source_manifest_sha256"] = fixture.sourceManifestSHA256
        result["plan"] = plan

        var receipt = result["receipt"] as! [String: Any]
        receipt["canonical_sha256"] = fixture.exact.receiptCanonicalSHA256
        receipt["export_plan_id"] = fixture.exact.exportPlanID
        receipt["export_receipt_id"] = fixture.exact.exportReceiptID
        result["receipt"] = receipt

        var verification = result["verification"] as! [String: Any]
        verification["canonical_sha256"] = fixture.exact.verificationCanonicalSHA256
        verification["export_plan_id"] = fixture.exact.exportPlanID
        verification["export_receipt_id"] = fixture.exact.exportReceiptID
        verification["export_verification_id"] = fixture.exact.exportVerificationID
        verification["source_manifest_sha256"] = fixture.sourceManifestSHA256
        result["verification"] = verification
        payload["result"] = result

        let data = try! JSONSerialization.data(
            withJSONObject: payload,
            options: [.sortedKeys, .withoutEscapingSlashes]
        )
        guard let response = String(bytes: data, encoding: .utf8) else {
            preconditionFailure("JSONSerialization must produce UTF-8 JSON")
        }
        return response
    }

    private struct ExportSurfaceParityFixture: Decodable {
        let exact: Exact
        let sourceManifestSHA256: String

        struct Exact: Decodable {
            let exportPlanID: String
            let exportReceiptID: String
            let exportVerificationID: String
            let planCanonicalSHA256: String
            let receiptCanonicalSHA256: String
            let verificationCanonicalSHA256: String

            enum CodingKeys: String, CodingKey {
                case exportPlanID = "export_plan_id"
                case exportReceiptID = "export_receipt_id"
                case exportVerificationID = "export_verification_id"
                case planCanonicalSHA256 = "plan_canonical_sha256"
                case receiptCanonicalSHA256 = "receipt_canonical_sha256"
                case verificationCanonicalSHA256 = "verification_canonical_sha256"
            }
        }

        enum CodingKeys: String, CodingKey {
            case exact
            case sourceManifestSHA256 = "source_manifest_sha256"
        }
    }

    private func exportSurfaceParityFixture() throws -> ExportSurfaceParityFixture {
        let repositoryRoot = URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
        let fixture = repositoryRoot
            .appendingPathComponent("tests/regressions/fixtures/phase4/export-surfaces.json")
        return try JSONDecoder().decode(
            ExportSurfaceParityFixture.self,
            from: Data(contentsOf: fixture)
        )
    }

    private func exportDryRunRequest() throws -> ExportDryRunRequest {
        try ExportDryRunRequest(
            bundle: "/tmp/source.vfbundle",
            containerID: "trainer-jsonl",
            containerVersion: 1,
            sourceTrustPolicy: .requireExternalDigest,
            expectedManifestSHA256: digest("a")
        )
    }

    private func exportExecuteRequest() throws -> ExportExecuteRequest {
        try ExportExecuteRequest(
            bundle: "/tmp/source.vfbundle",
            containerID: "trainer-jsonl",
            containerVersion: 1,
            sourceTrustPolicy: .requireExternalDigest,
            expectedManifestSHA256: digest("a"),
            destinationRoot: "/tmp/export",
            expectedExportPlanID: "export-plan-v1-\(digest("b"))"
        )
    }

    private func exportVerifyRequest() throws -> ExportVerifyRequest {
        try ExportVerifyRequest(
            bundle: "/tmp/source.vfbundle",
            containerID: "trainer-jsonl",
            containerVersion: 1,
            sourceTrustPolicy: .requireExternalDigest,
            expectedManifestSHA256: digest("a"),
            destinationRoot: "/tmp/export",
            expectedExportPlanID: "export-plan-v1-\(digest("b"))"
        )
    }

    private func digest(_ character: Character) -> String {
        String(repeating: String(character), count: 64)
    }

    private func recordedArguments(_ url: URL) throws -> [String] {
        try String(contentsOf: url, encoding: .utf8)
            .split(separator: "\n", omittingEmptySubsequences: true)
            .map(String.init)
    }

    private func compilePreflightRequest(root: URL) -> CompilePreflightRequest {
        CompilePreflightRequest(
            sources: [root.appendingPathComponent("source.txt")],
            sourceRoot: root,
            goal: "continue-a-passage",
            preset: "continue-a-passage.safe",
            representation: "prompt-and-completion"
        )
    }

    private func compilePreflightData(
        admitted: Bool = true,
        mutating mutation: ((inout [String: Any]) -> Void)? = nil
    ) throws -> Data {
        let digestA = String(repeating: "a", count: 64)
        let digestB = String(repeating: "b", count: 64)
        let refusalReasons: [[String: Any]] = admitted
            ? []
            : [[
                "code": "goal-evidence-unavailable",
                "detail_codes": ["target-boundary-missing"],
                "message": "The source does not supply the required target boundary.",
            ]]
        let source: [String: Any] = [
            "logical_path": "source.txt",
            "source_id": "source-v1-\(digestA)",
            "sha256": digestA,
            "size": 128,
            "input_family": "plain-text",
            "parser_id": "plain-text-v1",
            "parser_status": "complete",
            "parser_eligible": true,
            "goal_family_eligible": true,
            "evidence_status": admitted ? "available" : "missing",
            "admitted": admitted,
            "refusal_reasons": refusalReasons,
            "diagnostic_counts": [["code": "source-preserved", "count": 1]],
            "diagnostics": [[
                "diagnostic_id": "diagnostic-v1-\(digestB)",
                "code": "source-preserved",
                "severity": "info",
                "disposition": "preserved",
                "loss_kind": "none",
                "message": "Source text was preserved.",
            ]],
            "omitted_diagnostic_count": 0,
            "omission_reason": NSNull(),
            "exact_size_bytes": 640,
        ]
        let counts: [String: Any] = [
            "source_count": 1,
            "parser_eligible_source_count": 1,
            "family_eligible_source_count": 1,
            "evidence_eligible_source_count": admitted ? 1 : 0,
            "admitted_source_count": admitted ? 1 : 0,
            "candidate_count": admitted ? 2 : 0,
            "record_count": admitted ? 1 : 0,
            "pending_review_count": 0,
            "included_count": admitted ? 1 : 0,
            "excluded_count": admitted ? 1 : 0,
            "quarantined_count": 0,
        ]
        var payload: [String: Any] = [
            "schema_id": "veriformis.compile-preflight/v1",
            "request_digest": digestA,
            "captured_source_digest": digestB,
            "evaluated_through": admitted ? "split" : "construct",
            "admitted": admitted,
            "selection": [
                "requested_goal": "continue-a-passage",
                "requested_preset": "continue-a-passage.safe",
                "requested_representation": "prompt-and-completion",
                "instruction_supplied": false,
                "resolved": [
                    "goal_id": "continue-a-passage",
                    "preset_id": "continue-a-passage.safe",
                    "representation_id": "prompt-and-completion",
                    "objective": "continuation",
                    "row_schema": "prompt_completion",
                    "recipe_library_id": "finished-dataset-v1",
                    "consumer_profile": "veriformis-canonical-v1",
                    "settings_digest": digestA,
                    "cleaning_config_digest": digestB,
                    "segmentation": [
                        "strategy": "paragraph",
                        "size": 1000,
                        "overlap": 100,
                    ],
                    "construction": [
                        "split_ratio_ppm": 500_000,
                        "require_review": false,
                        "consumer_profile": "veriformis-canonical-v1",
                    ],
                    "curation": [
                        "minimum_target_characters": 80,
                        "balance_mode": "none",
                        "maximum_records_per_primary_source": NSNull(),
                        "evaluation_ratio_ppm": 200_000,
                        "evaluation_required": true,
                        "split_seed": "preflight-seed",
                    ],
                    "review_policy": "none",
                ],
            ],
            "counts": counts,
            "sources": [source],
            "incompatibilities": [],
            "missing_evidence": admitted ? [] : [[
                "diagnostic_id": "diagnostic-v1-\(digestA)",
                "code": "target-boundary-missing",
                "message": "The goal-specific target boundary is missing.",
                "pass_id": "construct",
                "source_ids": ["source-v1-\(digestA)"],
                "chunk_ids": [],
            ]],
            "expected_exclusion_counts": admitted ? [[
                "stage": "curate",
                "status": "excluded",
                "reason_code": "short-target",
                "count": 1,
            ]] : [],
            "expected_exclusions": admitted ? [[
                "stage": "curate",
                "subject_id": "record-v1-\(digestB)",
                "source_ids": ["source-v1-\(digestA)"],
                "status": "excluded",
                "reason_codes": ["short-target"],
            ]] : [],
            "omitted_expected_exclusion_count": 0,
            "coverage_blockers": [],
            "known_limitations": [[
                "code": "point-in-time-source-capture",
                "message": "Compile recaptures sources and may observe later changes.",
                "source_ids": [],
            ]],
            "omitted_diagnostic_count": 0,
        ]
        mutation?(&payload)
        return try JSONSerialization.data(
            withJSONObject: payload,
            options: [.sortedKeys, .withoutEscapingSlashes]
        )
    }

    private func compilePreflightHeredoc(admitted: Bool = true) throws -> String {
        let payload = String(decoding: try compilePreflightData(admitted: admitted), as: UTF8.self)
        return """
        cat <<'VERIFORMIS_COMPILE_PREFLIGHT_JSON'
        \(payload)
        VERIFORMIS_COMPILE_PREFLIGHT_JSON
        """
    }

    private func isolatedDefaults(
        output: URL
    ) throws -> (defaults: UserDefaults, name: String) {
        let name = "veriformis-tests-\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: name))
        defaults.set(output.path, forKey: "veriformis.workbench.defaultOutput")
        return (defaults, name)
    }

    @MainActor
    private func configureForPreflight(
        _ workbench: WorkbenchViewModel,
        source: URL,
        root: URL,
        output: URL
    ) throws {
        workbench.applyCatalogs(
            goals: try JSONDecoder().decode(GoalCatalog.self, from: goalCatalogData()),
            presets: try JSONDecoder().decode(
                RecipePresetCatalog.self,
                from: recipePresetsData()
            )
        )
        workbench.sourceURLs = [source]
        workbench.sourceRootURL = root
        workbench.outputDirectoryURL = output
    }

    @MainActor
    private func waitForTerminalPreflightState(
        _ workbench: WorkbenchViewModel,
        attempts: Int = 300
    ) async throws -> CompilePreflightState {
        for _ in 0 ..< attempts {
            switch workbench.compilePreflightState {
            case .ready, .unavailable:
                return workbench.compilePreflightState
            case .idle, .loading:
                try await Task.sleep(nanoseconds: 10_000_000)
            }
        }
        XCTFail("compile preflight did not reach a terminal state")
        return workbench.compilePreflightState
    }

    @MainActor
    private func waitForCompileToFinish(
        _ workbench: WorkbenchViewModel,
        attempts: Int = 300
    ) async throws {
        for _ in 0 ..< attempts where workbench.isRunning {
            try await Task.sleep(nanoseconds: 10_000_000)
        }
        XCTAssertFalse(workbench.isRunning, "compile did not finish")
    }

    @MainActor
    private func waitForTerminalGoalPreviewState(
        _ workbench: WorkbenchViewModel,
        attempts: Int = 300
    ) async throws -> GoalPreviewState {
        for _ in 0 ..< attempts {
            switch workbench.goalPreviewState {
            case .ready, .unavailable:
                return workbench.goalPreviewState
            case .idle, .loading:
                try await Task.sleep(nanoseconds: 10_000_000)
            }
        }
        XCTFail("goal preview did not reach a terminal state")
        return workbench.goalPreviewState
    }

    private func waitForFile(_ url: URL) async throws {
        for _ in 0 ..< 200 {
            if FileManager.default.fileExists(atPath: url.path) {
                return
            }
            try await Task.sleep(nanoseconds: 10_000_000)
        }
        XCTFail("timed out waiting for \(url.path)")
    }

    private struct GoalAcceptanceMatrixKey: CodingKey {
        let stringValue: String
        var intValue: Int? { nil }
        init?(stringValue: String) { self.stringValue = stringValue }
        init?(intValue: Int) { nil }
        init(_ value: String) { stringValue = value }
    }

    private struct GoalAcceptanceMatrixFixture: Decodable {
        static let expectedKeys: Set<String> = [
            "schema_id", "catalog_sha256", "preset_catalog_sha256",
            "source_fixtures", "cells",
        ]

        let schemaID: String
        let catalogSHA256: String
        let presetCatalogSHA256: String
        let sourceFixtures: [SourceFixture]
        let cells: [Cell]

        struct SourceFixture: Decodable {
            static let expectedKeys: Set<String> = [
                "source_fixture_id", "input_family", "logical_path", "raw_base64",
                "sha256", "size",
            ]

            let sourceFixtureID: String
            let inputFamily: String
            let logicalPath: String
            let rawBase64: String
            let sha256: String
            let size: Int

            init(from decoder: Decoder) throws {
                let container = try decoder.container(keyedBy: GoalAcceptanceMatrixKey.self)
                try GoalAcceptanceMatrixFixture.requireKeys(
                    container,
                    expected: Self.expectedKeys
                )
                sourceFixtureID = try container.decode(
                    String.self,
                    forKey: GoalAcceptanceMatrixKey("source_fixture_id")
                )
                inputFamily = try container.decode(
                    String.self,
                    forKey: GoalAcceptanceMatrixKey("input_family")
                )
                logicalPath = try container.decode(
                    String.self,
                    forKey: GoalAcceptanceMatrixKey("logical_path")
                )
                rawBase64 = try container.decode(
                    String.self,
                    forKey: GoalAcceptanceMatrixKey("raw_base64")
                )
                sha256 = try container.decode(
                    String.self,
                    forKey: GoalAcceptanceMatrixKey("sha256")
                )
                size = try container.decode(
                    Int.self,
                    forKey: GoalAcceptanceMatrixKey("size")
                )
            }
        }

        struct Cell: Decodable {
            static let expectedKeys: Set<String> = [
                "cell_id", "source_fixture_ids", "input_family", "goal_id", "preset_id",
                "representation_id", "instruction", "cleaning_rules", "cleaning_custom",
                "chunk_size", "chunk_overlap", "evaluation_required", "recipe_id",
                "row_set_sha256", "manifest_sha256", "loss_policy", "loss_boundary",
                "context_row_keys", "supervised_row_key", "supervision_sha256",
                "exclusions",
            ]

            let cellID: String
            let sourceFixtureIDs: [String]
            let inputFamily: String
            let goalID: String
            let presetID: String
            let representationID: String
            let instruction: String?
            let cleaningRules: String
            let cleaningCustom: String
            let chunkSize: Int?
            let chunkOverlap: Int?
            let evaluationRequired: Bool
            let recipeID: String
            let rowSetSHA256: String
            let manifestSHA256: String
            let lossPolicy: String
            let lossBoundary: String
            let contextRowKeys: [String]
            let supervisedRowKey: String
            let supervisionSHA256: String
            let exclusions: [Exclusion]

            struct Exclusion: Decodable, Equatable {
                static let expectedKeys: Set<String> = [
                    "record_id", "status", "reason_codes",
                ]

                let recordID: String
                let status: String
                let reasonCodes: [String]

                init(recordID: String, status: String, reasonCodes: [String]) {
                    self.recordID = recordID
                    self.status = status
                    self.reasonCodes = reasonCodes
                }

                init(from decoder: Decoder) throws {
                    let container = try decoder.container(
                        keyedBy: GoalAcceptanceMatrixKey.self
                    )
                    try GoalAcceptanceMatrixFixture.requireKeys(
                        container,
                        expected: Self.expectedKeys
                    )
                    recordID = try container.decode(
                        String.self,
                        forKey: GoalAcceptanceMatrixKey("record_id")
                    )
                    status = try container.decode(
                        String.self,
                        forKey: GoalAcceptanceMatrixKey("status")
                    )
                    reasonCodes = try container.decode(
                        [String].self,
                        forKey: GoalAcceptanceMatrixKey("reason_codes")
                    )
                }
            }

            init(from decoder: Decoder) throws {
                let container = try decoder.container(keyedBy: GoalAcceptanceMatrixKey.self)
                try GoalAcceptanceMatrixFixture.requireKeys(
                    container,
                    expected: Self.expectedKeys
                )
                cellID = try container.decode(
                    String.self,
                    forKey: GoalAcceptanceMatrixKey("cell_id")
                )
                sourceFixtureIDs = try container.decode(
                    [String].self,
                    forKey: GoalAcceptanceMatrixKey("source_fixture_ids")
                )
                inputFamily = try container.decode(
                    String.self,
                    forKey: GoalAcceptanceMatrixKey("input_family")
                )
                goalID = try container.decode(
                    String.self,
                    forKey: GoalAcceptanceMatrixKey("goal_id")
                )
                presetID = try container.decode(
                    String.self,
                    forKey: GoalAcceptanceMatrixKey("preset_id")
                )
                representationID = try container.decode(
                    String.self,
                    forKey: GoalAcceptanceMatrixKey("representation_id")
                )
                instruction = try container.decodeIfPresent(
                    String.self,
                    forKey: GoalAcceptanceMatrixKey("instruction")
                )
                cleaningRules = try container.decode(
                    String.self,
                    forKey: GoalAcceptanceMatrixKey("cleaning_rules")
                )
                cleaningCustom = try container.decode(
                    String.self,
                    forKey: GoalAcceptanceMatrixKey("cleaning_custom")
                )
                chunkSize = try container.decodeIfPresent(
                    Int.self,
                    forKey: GoalAcceptanceMatrixKey("chunk_size")
                )
                chunkOverlap = try container.decodeIfPresent(
                    Int.self,
                    forKey: GoalAcceptanceMatrixKey("chunk_overlap")
                )
                evaluationRequired = try container.decode(
                    Bool.self,
                    forKey: GoalAcceptanceMatrixKey("evaluation_required")
                )
                recipeID = try container.decode(
                    String.self,
                    forKey: GoalAcceptanceMatrixKey("recipe_id")
                )
                rowSetSHA256 = try container.decode(
                    String.self,
                    forKey: GoalAcceptanceMatrixKey("row_set_sha256")
                )
                manifestSHA256 = try container.decode(
                    String.self,
                    forKey: GoalAcceptanceMatrixKey("manifest_sha256")
                )
                lossPolicy = try container.decode(
                    String.self,
                    forKey: GoalAcceptanceMatrixKey("loss_policy")
                )
                lossBoundary = try container.decode(
                    String.self,
                    forKey: GoalAcceptanceMatrixKey("loss_boundary")
                )
                contextRowKeys = try container.decode(
                    [String].self,
                    forKey: GoalAcceptanceMatrixKey("context_row_keys")
                )
                supervisedRowKey = try container.decode(
                    String.self,
                    forKey: GoalAcceptanceMatrixKey("supervised_row_key")
                )
                supervisionSHA256 = try container.decode(
                    String.self,
                    forKey: GoalAcceptanceMatrixKey("supervision_sha256")
                )
                exclusions = try container.decode(
                    [Exclusion].self,
                    forKey: GoalAcceptanceMatrixKey("exclusions")
                )
            }
        }

        init(from decoder: Decoder) throws {
            let container = try decoder.container(keyedBy: GoalAcceptanceMatrixKey.self)
            try Self.requireKeys(container, expected: Self.expectedKeys)
            schemaID = try container.decode(
                String.self,
                forKey: GoalAcceptanceMatrixKey("schema_id")
            )
            catalogSHA256 = try container.decode(
                String.self,
                forKey: GoalAcceptanceMatrixKey("catalog_sha256")
            )
            presetCatalogSHA256 = try container.decode(
                String.self,
                forKey: GoalAcceptanceMatrixKey("preset_catalog_sha256")
            )
            sourceFixtures = try container.decode(
                [SourceFixture].self,
                forKey: GoalAcceptanceMatrixKey("source_fixtures")
            )
            cells = try container.decode(
                [Cell].self,
                forKey: GoalAcceptanceMatrixKey("cells")
            )
        }

        private static func requireKeys(
            _ container: KeyedDecodingContainer<GoalAcceptanceMatrixKey>,
            expected: Set<String>
        ) throws {
            let actual = Set(container.allKeys.map(\.stringValue))
            guard actual == expected else {
                throw DecodingError.dataCorrupted(
                    DecodingError.Context(
                        codingPath: container.codingPath,
                        debugDescription: "goal acceptance matrix key drift: expected \(expected.sorted()), got \(actual.sorted())"
                    )
                )
            }
        }
    }

    private enum GoalAcceptanceMatrixTestError: LocalizedError {
        case commandFailed(operation: String, exitCode: Int32, output: String)
        case outputTruncated(operation: String)
        case invalidBundle(String)
        case invalidPreview(String)

        var errorDescription: String? {
            switch self {
            case .commandFailed(let operation, let exitCode, let output):
                return "real CLI \(operation) failed (exit \(exitCode)): \(output)"
            case .outputTruncated(let operation):
                return "real CLI \(operation) output was truncated"
            case .invalidBundle(let message):
                return "sealed bundle is invalid: \(message)"
            case .invalidPreview(let message):
                return "goal preview is invalid: \(message)"
            }
        }
    }

    private func goalAcceptanceMatrixFixture() throws -> GoalAcceptanceMatrixFixture {
        let fixture = testRepositoryRoot()
            .appendingPathComponent(
                "tests/regressions/fixtures/phase6/goal-acceptance-matrix.json"
            )
        return try JSONDecoder().decode(
            GoalAcceptanceMatrixFixture.self,
            from: Data(contentsOf: fixture)
        )
    }

    private func testRepositoryRoot() -> URL {
        URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
    }

    private func sha256Hex(_ data: Data) -> String {
        SHA256.hash(data: data)
            .map { String(format: "%02x", $0) }
            .joined()
    }

    private func requireSuccessfulRealCLI(
        _ cli: VeriformisCLI,
        arguments: [String],
        operation: String
    ) async throws -> CLIProcessResult {
        let result = try await cli.run(arguments: arguments)
        guard !result.outputTruncated else {
            throw GoalAcceptanceMatrixTestError.outputTruncated(operation: operation)
        }
        guard result.exitCode == 0 else {
            throw GoalAcceptanceMatrixTestError.commandFailed(
                operation: operation,
                exitCode: result.exitCode,
                output: result.combinedOutput
            )
        }
        return result
    }

    private struct BundleValidationIdentity {
        let recipeID: String
        let rowSetSHA256: String
    }

    private func bundleValidationIdentity(_ bundle: URL) throws -> BundleValidationIdentity {
        let validation = bundle.appendingPathComponent("validation.json")
        let object = try JSONSerialization.jsonObject(with: Data(contentsOf: validation))
        guard let root = object as? [String: Any],
              let snapshot = root["snapshot"] as? [String: Any],
              let recipeID = snapshot["recipe_id"] as? String,
              !recipeID.isEmpty,
              let bindings = snapshot["artifact_bindings"] as? [[String: Any]]
        else {
            throw GoalAcceptanceMatrixTestError.invalidBundle(
                "validation snapshot identity is missing"
            )
        }
        let rowSetBindings = bindings.filter { $0["role"] as? String == "row-set" }
        guard rowSetBindings.count == 1,
              let rowSetSHA256 = rowSetBindings[0]["sha256"] as? String,
              !rowSetSHA256.isEmpty
        else {
            throw GoalAcceptanceMatrixTestError.invalidBundle(
                "validation snapshot must contain exactly one row-set binding"
            )
        }
        return BundleValidationIdentity(
            recipeID: recipeID,
            rowSetSHA256: rowSetSHA256
        )
    }

    private func goalPreviewSupervisionSHA256(_ preview: GoalPreview) throws -> String {
        var boundaries: [[String: Any]] = []
        for record in preview.records {
            guard let supervisedValue = record.supervisedValue else {
                throw GoalAcceptanceMatrixTestError.invalidPreview(
                    "record \(record.recordID) has no supervised value"
                )
            }
            let scalarCount = supervisedValue.unicodeScalars.count
            guard record.supervised.start == 0,
                  record.supervised.end == scalarCount
            else {
                throw GoalAcceptanceMatrixTestError.invalidPreview(
                    "record \(record.recordID) span does not use Unicode scalar offsets"
                )
            }
            boundaries.append(
                [
                    "record_id": record.recordID,
                    "context_row_keys": record.contextRowKeys,
                    "row_key": record.supervised.rowKey,
                    "start": record.supervised.start,
                    "end": record.supervised.end,
                    "target_sha256": sha256Hex(Data(supervisedValue.utf8)),
                ]
            )
        }
        let canonical = try JSONSerialization.data(
            withJSONObject: boundaries,
            options: [.sortedKeys, .withoutEscapingSlashes]
        )
        return sha256Hex(canonical)
    }

    private func recipePresetsFixtureURL() -> URL {
        URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .appendingPathComponent("tests/regressions/fixtures/phase6/recipe-presets.json")
    }

    private func recipePresetsData(
        mutating mutation: ((inout [String: Any]) -> Void)? = nil
    ) throws -> Data {
        let stored = try Data(contentsOf: recipePresetsFixtureURL())
        guard mutation != nil else { return stored }
        var payload = try XCTUnwrap(JSONSerialization.jsonObject(with: stored) as? [String: Any])
        mutation?(&payload)
        return try JSONSerialization.data(withJSONObject: payload, options: [.sortedKeys])
    }

    private func goalPreviewFixtureURL() -> URL {
        URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .appendingPathComponent("tests/regressions/fixtures/phase6/goal-preview.json")
    }

    private func goalPreviewData(
        mutating mutation: ((inout [String: Any]) -> Void)? = nil
    ) throws -> Data {
        let stored = try Data(contentsOf: goalPreviewFixtureURL())
        guard mutation != nil else { return stored }
        var payload = try XCTUnwrap(
            JSONSerialization.jsonObject(with: stored) as? [String: Any]
        )
        mutation?(&payload)
        return try JSONSerialization.data(withJSONObject: payload, options: [.sortedKeys])
    }

    private func goalCatalogFixtureURL() -> URL {
        URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .appendingPathComponent("tests/regressions/fixtures/phase6/goal-catalog.json")
    }

    private func goalCatalogData(
        mutating mutation: ((inout [String: Any]) -> Void)? = nil
    ) throws -> Data {
        let stored = try Data(contentsOf: goalCatalogFixtureURL())
        guard mutation != nil else { return stored }
        var payload = try XCTUnwrap(
            JSONSerialization.jsonObject(with: stored) as? [String: Any]
        )
        mutation?(&payload)
        return try JSONSerialization.data(withJSONObject: payload, options: [.sortedKeys])
    }

    private func taxonomyData(
        mutating mutation: ((inout [String: [String]]) -> Void)? = nil
    ) throws -> Data {
        var payload = taxonomyPayload()
        mutation?(&payload)
        return try JSONSerialization.data(withJSONObject: payload, options: [.sortedKeys])
    }

    private func taxonomyHeredoc() throws -> String {
        let payload = String(decoding: try taxonomyData(), as: UTF8.self)
        return """
        cat <<'VERIFORMIS_TAXONOMY_JSON'
        \(payload)
        VERIFORMIS_TAXONOMY_JSON
        """
    }

    private func temporaryTestDirectory(_ label: String) -> URL {
        FileManager.default.temporaryDirectory
            .appendingPathComponent("veriformis-\(label)-\(UUID().uuidString)")
    }

    private func writeExecutable(_ url: URL, script: String) throws {
        try Data(script.utf8).write(to: url)
        try FileManager.default.setAttributes(
            [.posixPermissions: 0o755],
            ofItemAtPath: url.path
        )
    }

    @MainActor
    private func waitForTerminalTaxonomyState(
        _ workbench: WorkbenchViewModel
    ) async throws -> TaxonomyHelpState {
        for _ in 0 ..< 200 {
            switch workbench.taxonomyHelpState {
            case .ready, .unavailable:
                return workbench.taxonomyHelpState
            case .idle, .loading:
                try await Task.sleep(nanoseconds: 10_000_000)
            }
        }
        XCTFail("taxonomy discovery did not reach a terminal state")
        return workbench.taxonomyHelpState
    }
}
