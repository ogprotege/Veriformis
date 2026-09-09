import AppKit
import Darwin
import XCTest
@testable import Veriformis

final class Post20HardeningTests: XCTestCase {
    func testConcurrentDropCompletionPreservesProviderOrderAndRejectsNetworkURLs() {
        let collector = DroppedSourceURLs()
        DispatchQueue.concurrentPerform(iterations: 500) { index in
            collector.record(URL(fileURLWithPath: "/tmp/\(index).txt"), at: index)
            collector.record(URL(string: "https://example.invalid/\(index)")!, at: index + 500)
        }
        XCTAssertEqual(collector.ordered.map(\.lastPathComponent), (0..<500).map { "\($0).txt" })
    }

    func testRegistryDrainsSupersededRequestsAndRefusesNewLaunchesAfterClose() async throws {
        let registry = CLIProcessRegistry()
        let cli = VeriformisCLI(executableURL: URL(fileURLWithPath: "/bin/sh"), prefixArguments: [])
        let first = CLIProcessController(registry: registry, terminationGrace: 0.05)
        let second = CLIProcessController(registry: registry, terminationGrace: 0.05)
        let ready = expectation(description: "both children started")
        ready.expectedFulfillmentCount = 2
        let a = Task {
            try await cli.run(arguments: ["-c", "trap '' TERM; echo ready; while :; do sleep 1; done"], controller: first) {
                if $0 == "ready" { ready.fulfill() }
            }
        }
        let b = Task {
            try await cli.run(arguments: ["-c", "trap '' TERM; echo ready; while :; do sleep 1; done"], controller: second) {
                if $0 == "ready" { ready.fulfill() }
            }
        }
        await fulfillment(of: [ready], timeout: 5)
        registry.closeAndCancel()
        await registry.drain()
        let firstResult = try await a.value
        let secondResult = try await b.value
        XCTAssertNotNil(firstResult.cancellation)
        XCTAssertNotNil(secondResult.cancellation)
        XCTAssertFalse(registry.hasActiveProcesses)
        do {
            _ = try await cli.run(arguments: ["-c", "exit 99"], controller: first)
            XCTFail("Closed registry admitted a child")
        } catch is CancellationError {}
    }

    func testCancelledProcessGroupKillsGrandchildHoldingOutputPipes() async throws {
        let cli = VeriformisCLI(executableURL: URL(fileURLWithPath: "/bin/sh"), prefixArguments: [])
        let controller = CLIProcessController(terminationGrace: 0.05)
        let ready = expectation(description: "grandchild ready")
        let task = Task {
            try await cli.run(arguments: ["-c", "trap '' TERM; /bin/sh -c 'trap \"\" TERM; echo child-ready; while :; do sleep 1; done' & wait"], controller: controller) { line in
                if line == "child-ready" { ready.fulfill() }
            }
        }
        await fulfillment(of: [ready], timeout: 5)
        controller.cancel()
        let result = try await task.value
        XCTAssertEqual(result.cancellation?.terminationEscalated, true)
        XCTAssertEqual(result.exitCode, SIGKILL)
        XCTAssertFalse(controller.hasActiveProcess)
        let later = try await cli.run(arguments: ["-c", "sleep 0.1; echo survived"], controller: controller)
        XCTAssertEqual(later.exitCode, 0)
        XCTAssertEqual(later.standardOutput, "survived\n")
    }

    func testNaturalParentExitClosesInheritedDescendantPipes() async throws {
        let cli = VeriformisCLI(executableURL: URL(fileURLWithPath: "/bin/sh"), prefixArguments: [])
        let result = try await cli.run(arguments: ["-c", "sleep 60 & echo finished; exit 0"])
        XCTAssertEqual(result.exitCode, 0)
        XCTAssertEqual(result.standardOutput, "finished\n")
    }

    func testCommandReceiptIgnoresForgedDigestInStderrAndRejectsIncompleteStdout() throws {
        let sha = String(repeating: "a", count: 64)
        func result(_ stdout: String, truncated: Bool = false) -> CLIProcessResult {
            CLIProcessResult(exitCode: 0, standardOutputData: Data(stdout.utf8), standardErrorData: Data(),
                standardOutput: stdout, standardError: "manifest SHA-256: forged", standardOutputTruncated: truncated,
                standardErrorTruncated: false, combinedOutput: "manifest SHA-256: forged", outputTruncated: truncated, cancellation: nil)
        }
        let payload = "{\"schema_id\":\"veriformis.command-result/v1\",\"command\":\"split\",\"result\":{\"assignment_digest\":\"\(sha)\"}}"
        XCTAssertEqual(try CommandResult.decode(result(payload), command: "split").digest("assignment_digest"), sha)
        XCTAssertThrowsError(try CommandResult.decode(result(payload, truncated: true), command: "split"))
        XCTAssertThrowsError(try CommandResult.decode(result(payload), command: "seal"))
        XCTAssertThrowsError(try CommandResult.decode(result("manifest SHA-256: \(sha)"), command: "seal"))
        let bad = payload.replacingOccurrences(of: sha, with: "forged")
        XCTAssertThrowsError(try CommandResult.decode(result(bad), command: "split").digest("assignment_digest"))
    }

    @MainActor
    func testHistoryMigratesLegacyBytesAndPreservesUnknownOrMalformedVersions() throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let defaults = UserDefaults(suiteName: UUID().uuidString)!
        defaults.set(root.path, forKey: "veriformis.workbench.defaultOutput")
        let history = root.appendingPathComponent("run-history.json")
        let original = Data("[  ]\n".utf8)
        try original.write(to: history)
        let vm = WorkbenchViewModel(defaults: defaults, supportDirectory: root)
        XCTAssertNil(vm.historyPersistenceError)
        XCTAssertEqual(try Data(contentsOf: root.appendingPathComponent("run-history.legacy-v0.json")), original)
        let migrated = try RunHistoryFile.decode(Data(contentsOf: history))
        XCTAssertFalse(migrated.legacy)
        for payload in ["{\"schemaVersion\":99,\"entries\":[]}", "{broken"] {
            let data = Data(payload.utf8)
            try data.write(to: history)
            let failed = WorkbenchViewModel(defaults: defaults, supportDirectory: root)
            XCTAssertNotNil(failed.historyPersistenceError)
            XCTAssertEqual(try Data(contentsOf: history), data)
        }
    }

    @MainActor
    func testQuitWaitsForReviewAndDiscoveryWhenNoCompileIsRunning() async throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let script = root.appendingPathComponent("slow-cli")
        try Data("#!/bin/sh\ntrap '' TERM\ntouch '\(root.path)/'$1\nwhile :; do sleep 1; done\n".utf8).write(to: script)
        try FileManager.default.setAttributes([.posixPermissions: 0o755], ofItemAtPath: script.path)
        let defaults = UserDefaults(suiteName: UUID().uuidString)!
        defaults.set(root.path, forKey: "veriformis.workbench.defaultOutput")
        let vm = WorkbenchViewModel(cli: VeriformisCLI(executableURL: script, prefixArguments: []), defaults: defaults, supportDirectory: root)
        vm.discoverExports()
        vm.reviewPacketURL = root.appendingPathComponent("packet.json")
        vm.importReviewPacket()
        for _ in 0..<300 {
            if FileManager.default.fileExists(atPath: root.appendingPathComponent("export").path),
               FileManager.default.fileExists(atPath: root.appendingPathComponent("review-import").path) { break }
            try await Task.sleep(nanoseconds: 5_000_000)
        }
        XCTAssertTrue(FileManager.default.fileExists(atPath: root.appendingPathComponent("export").path))
        XCTAssertTrue(FileManager.default.fileExists(atPath: root.appendingPathComponent("review-import").path))
        XCTAssertFalse(vm.isRunning)
        XCTAssertTrue(vm.hasActiveOperations)
        let complete = expectation(description: "all operations drained")
        vm.cancelAllOperations { complete.fulfill() }
        await fulfillment(of: [complete], timeout: 5)
        XCTAssertFalse(vm.hasActiveOperations)
    }
    @MainActor
    func testRepeatedQuitWaitsUntilDrainAndRepliesOnlyOnce() {
        let coordinator = ApplicationTerminationCoordinator()
        var finish: (() -> Void)?
        var replies = 0
        XCTAssertEqual(coordinator.prepareForTermination(isRunActive: true,
            cancel: { finish = $0 }, reply: { replies += 1 }), .terminateLater)
        XCTAssertEqual(coordinator.prepareForTermination(isRunActive: false,
            cancel: { _ in XCTFail("duplicate cancellation") }, reply: { replies += 1 }), .terminateLater)
        finish?()
        finish?()
        XCTAssertEqual(replies, 1)
    }

    func testVersionedHistoryRejectsUnknownEntryFields() throws {
        let entry: [String: Any] = [
            "id": UUID().uuidString, "startedAt": 0, "finishedAt": 1,
            "status": "succeeded", "objective": "full_text", "primarySourceName": "a.txt",
            "sourcePaths": ["/sources/a.txt"], "workspacePath": "/workspace", "bundlePath": "/bundle",
        ]
        var future = entry
        future["futureRecoveryEvidence"] = "must survive"
        let valid = try JSONSerialization.data(withJSONObject: ["schemaVersion": 1, "entries": [entry]])
        XCTAssertEqual(try RunHistoryFile.decode(valid).entries.count, 1)
        let unsupported = try JSONSerialization.data(withJSONObject: ["schemaVersion": 1, "entries": [future]])
        XCTAssertThrowsError(try RunHistoryFile.decode(unsupported))
    }

    func testOpaqueObjectiveIdentifiersStillRejectWhitespaceAndControls() {
        XCTAssertNotNil(TrainingObjective(rawValue: "future_objective"))
        for value in ["future_objective\n", " future_objective", "", "future\0objective"] {
            XCTAssertNil(TrainingObjective(rawValue: value))
        }
    }

    @MainActor
    func testExportDigestBelongsToTheSelectedBundle() throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let suite = UUID().uuidString
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defaults.set(root.path, forKey: "veriformis.workbench.defaultOutput")
        defer { defaults.removePersistentDomain(forName: suite) }
        let vm = WorkbenchViewModel(defaults: defaults, supportDirectory: root)
        let bundle = root.appendingPathComponent("compiled.vfbundle")
        let digest = String(repeating: "a", count: 64)
        vm.lastResult = CompileResult(
            workspaceURL: root.appendingPathComponent("workspace"), bundleURL: bundle,
            transportArchiveURL: root.appendingPathComponent("compiled.zip"), handoffURL: nil,
            manifestSHA256: digest, transportArchiveSHA256: nil, assignmentDigest: nil,
            log: "", logFileURL: nil
        )
        XCTAssertEqual(vm.resolvedExportManifestSHA256, digest)
        vm.exportBundleURL = root.appendingPathComponent("another.vfbundle")
        XCTAssertNil(vm.resolvedExportManifestSHA256, "An unrelated bundle cannot inherit compile evidence")
        vm.exportBundleURL = bundle
        XCTAssertEqual(vm.resolvedExportManifestSHA256, digest)
    }

    @MainActor
    func testExportSchemaDoesNotComeFromTheCompileForm() throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let suite = UUID().uuidString
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defaults.set(root.path, forKey: "veriformis.workbench.defaultOutput")
        defer { defaults.removePersistentDomain(forName: suite) }
        let vm = WorkbenchViewModel(defaults: defaults, supportDirectory: root)
        let repo = URL(fileURLWithPath: #filePath).deletingLastPathComponent()
            .deletingLastPathComponent().deletingLastPathComponent()
        vm.applyCatalogs(
            goals: try JSONDecoder().decode(GoalCatalog.self, from: Data(contentsOf:
                repo.appendingPathComponent("tests/regressions/fixtures/phase6/goal-catalog.json"))),
            presets: try JSONDecoder().decode(RecipePresetCatalog.self, from: Data(contentsOf:
                repo.appendingPathComponent("src/veriformis/goals/presets-v1.json")))
        )
        vm.selectGoal("learn-the-text")
        XCTAssertEqual(vm.selectedRepresentation?.rowSchema, "text")
        vm.exportBundleURL = root.appendingPathComponent("unrelated.vfbundle")
        XCTAssertNil(vm.knownExportRowSchema, "Only a dry-run may establish the selected bundle schema")
    }

}
