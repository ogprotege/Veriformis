import XCTest
@testable import Veriformis

final class CLIBridgeTests: XCTestCase {
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
        XCTAssertEqual(plan[8].arguments, ["seal", workspace.path, "-o", bundle.path])
    }

    func testCompilePlanCanDisableHandoff() {
        let plan = VeriformisCLI.compilePlan(
            sources: [URL(fileURLWithPath: "/data/a.txt")],
            sourceRoot: URL(fileURLWithPath: "/data"),
            workspace: URL(fileURLWithPath: "/tmp/ws"),
            bundle: URL(fileURLWithPath: "/tmp/b.vfbundle"),
            objective: .fullText,
            allowEmptyEvaluation: false,
            splitRatioPPM: 500_000,
            includeHandoff: false
        )
        XCTAssertTrue(plan.last!.arguments.contains("--no-aptus-handoff"))
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

    func testMissingCLIErrorMentionsPrerequisites() throws {
        let message = WorkbenchError.missingCLI.localizedDescription
        XCTAssertTrue(message.contains("uv sync"))
        XCTAssertTrue(message.contains("VERIFORMIS_CLI"))
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
}
