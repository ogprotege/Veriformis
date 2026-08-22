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
            printf '{"error":{"code":"invalid-data","message":"not registered"},"operation":"%s","result":null,"schema_version":"veriformis.export-surface-response/v1","status":"error"}\\n' "$operation"
            exit 1
            """
        )
        let cli = VeriformisCLI(executableURL: executable, prefixArguments: [])
        let dryRun = try exportDryRunRequest()
        let inspect = try ExportInspectRequest(destinationRoot: "/tmp/export")
        let execute = try exportExecuteRequest()
        let verify = try exportVerifyRequest()

        let discovery = try await cli.discoverExports()
        XCTAssertEqual(discovery.status, .error)
        XCTAssertEqual(try recordedArguments(arguments), ["export", "discover"])

        let dryRunResponse = try await cli.dryRunExport(dryRun)
        XCTAssertEqual(dryRunResponse.status, .error)
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
        XCTAssertFalse(
            [
                try dryRun.canonicalJSON(),
                try inspect.canonicalJSON(),
                try execute.canonicalJSON(),
                try verify.canonicalJSON(),
            ].contains { $0.contains("force") }
        )
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
        XCTAssertEqual(
            plan[3].arguments,
            [
                "construct", workspace.path, "--objective", "continuation",
                "--consumer-profile", "aptus-handoff-v1",
                "--split-ratio-ppm", "400000",
            ]
        )
        XCTAssertTrue(plan[4].arguments.contains("--allow-empty-evaluation"))
        XCTAssertEqual(plan[6].stage.rawValue, "format")
        XCTAssertEqual(plan[6].arguments, ["format", workspace.path])
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
        XCTAssertFalse(
            plan.flatMap(\.arguments).contains { $0.lowercased().contains("aptus") }
        )
    }

    @MainActor
    func testDefaultCompileFailsClosedAndMatchesCLISplitDefault() throws {
        XCTAssertFalse(WorkbenchViewModel.defaultAllowEmptyEvaluation)
        XCTAssertEqual(WorkbenchViewModel.defaultSplitRatioPPM, 500_000)

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

        // A fresh workbench must start from the CLI's fail-closed defaults.
        let workbench = WorkbenchViewModel(defaults: defaults, supportDirectory: support)
        XCTAssertFalse(workbench.allowEmptyEvaluation)
        XCTAssertEqual(workbench.splitRatioPPM, 500_000)

        // The default compile plan must never weaken the curate gate…
        let workspace = URL(fileURLWithPath: "/tmp/ws")
        let plan = VeriformisCLI.compilePlan(
            sources: [URL(fileURLWithPath: "/data/a.txt")],
            sourceRoot: URL(fileURLWithPath: "/data"),
            workspace: workspace,
            bundle: URL(fileURLWithPath: "/tmp/out.vfbundle"),
            objective: .continuation,
            allowEmptyEvaluation: workbench.allowEmptyEvaluation,
            splitRatioPPM: workbench.splitRatioPPM
        )
        XCTAssertFalse(
            plan.flatMap(\.arguments).contains("--allow-empty-evaluation"),
            "default GUI compile must match the CLI --require-evaluation default"
        )
        // …and a continuation plan must carry the CLI's split-ratio default.
        let construct = try XCTUnwrap(plan.first { $0.stage == .construct })
        guard let flagIndex = construct.arguments.firstIndex(of: "--split-ratio-ppm") else {
            return XCTFail("continuation plan must pass --split-ratio-ppm")
        }
        XCTAssertEqual(construct.arguments[construct.arguments.index(after: flagIndex)], "500000")
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
        ]
    }

    private func exportDiscoveryResponse() -> String {
        "{\"error\":null,\"operation\":\"discover\",\"result\":{\"profiles\":[],\"schema_version\":\"veriformis.export-discovery/v1\"},\"schema_version\":\"veriformis.export-surface-response/v1\",\"status\":\"ok\"}"
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

    private func waitForFile(_ url: URL) async throws {
        for _ in 0 ..< 200 {
            if FileManager.default.fileExists(atPath: url.path) {
                return
            }
            try await Task.sleep(nanoseconds: 10_000_000)
        }
        XCTFail("timed out waiting for \(url.path)")
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
