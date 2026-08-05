import Foundation

/// Thin process adapter. Stage policy lives in Python `PipelineService` / CLI.
struct VeriformisCLI: Sendable {
    let executableURL: URL
    let prefixArguments: [String]

    /// Resolve the CLI: env override, PATH `veriformis`, or repo-local `uv run veriformis`.
    static func resolve(
        repositoryRoot: URL? = nil,
        fileManager: FileManager = .default
    ) throws -> VeriformisCLI {
        if let override = ProcessInfo.processInfo.environment["VERIFORMIS_CLI"], !override.isEmpty {
            let url = URL(fileURLWithPath: override)
            guard fileManager.isExecutableFile(atPath: url.path) else {
                throw WorkbenchError.missingCLI
            }
            return VeriformisCLI(executableURL: url, prefixArguments: [])
        }

        if let pathCLI = which("veriformis", fileManager: fileManager) {
            return VeriformisCLI(executableURL: pathCLI, prefixArguments: [])
        }

        let root = repositoryRoot ?? developmentRepositoryRoot()
        if let root {
            let uv = which("uv", fileManager: fileManager) ?? URL(fileURLWithPath: "/opt/homebrew/bin/uv")
            if fileManager.isExecutableFile(atPath: uv.path) {
                return VeriformisCLI(
                    executableURL: uv,
                    prefixArguments: ["run", "--directory", root.path, "veriformis"]
                )
            }
        }

        throw WorkbenchError.missingCLI
    }

    static func developmentRepositoryRoot(
        bundle: Bundle = .main,
        fileManager: FileManager = .default
    ) -> URL? {
        if let env = ProcessInfo.processInfo.environment["VERIFORMIS_DEVELOPMENT_REPOSITORY_ROOT"],
           !env.isEmpty
        {
            return URL(fileURLWithPath: env)
        }
        // Debug builds may embed the repo root via Xcode build setting.
        if let builtIn = bundle.object(forInfoDictionaryKey: "VERIFORMIS_DEVELOPMENT_REPOSITORY_ROOT") as? String,
           !builtIn.isEmpty
        {
            return URL(fileURLWithPath: builtIn)
        }
        // Walk up from CWD for `uv run` style launches during development.
        var dir = URL(fileURLWithPath: fileManager.currentDirectoryPath)
        for _ in 0 ..< 6 {
            let marker = dir.appendingPathComponent("pyproject.toml")
            if fileManager.fileExists(atPath: marker.path) {
                return dir
            }
            dir.deleteLastPathComponent()
        }
        return nil
    }

    func buildArguments(_ stageArguments: [String]) -> [String] {
        prefixArguments + stageArguments
    }

    /// Build the ordered stage command list the workbench will execute.
    static func compilePlan(
        sources: [URL],
        sourceRoot: URL,
        workspace: URL,
        bundle: URL,
        objective: TrainingObjective,
        allowEmptyEvaluation: Bool,
        splitRatioPPM: Int,
        includeHandoff: Bool
    ) -> [StageCommand] {
        var parseArgs = ["parse"]
        parseArgs.append(contentsOf: sources.map(\.path))
        parseArgs.append(contentsOf: ["-o", workspace.path, "--source-root", sourceRoot.path])

        var constructArgs = ["construct", workspace.path, "--objective", objective.rawValue]
        if objective == .continuation {
            constructArgs.append(contentsOf: ["--split-ratio-ppm", String(splitRatioPPM)])
        }

        var curateArgs = ["curate", workspace.path]
        if allowEmptyEvaluation {
            curateArgs.append("--allow-empty-evaluation")
        }

        var sealArgs = ["seal", workspace.path, "-o", bundle.path]
        if !includeHandoff {
            sealArgs.append("--no-aptus-handoff")
        }

        return [
            StageCommand(stage: .parse, arguments: parseArgs),
            StageCommand(stage: .clean, arguments: ["clean", workspace.path]),
            StageCommand(stage: .chunk, arguments: ["chunk", workspace.path]),
            StageCommand(stage: .construct, arguments: constructArgs),
            StageCommand(stage: .curate, arguments: curateArgs),
            StageCommand(stage: .split, arguments: ["split", workspace.path]),
            StageCommand(stage: .format, arguments: ["format", workspace.path]),
            StageCommand(stage: .validate, arguments: ["validate", workspace.path]),
            StageCommand(stage: .seal, arguments: sealArgs),
        ]
    }

    @discardableResult
    func run(
        arguments: [String],
        workingDirectory: URL? = nil,
        onOutputLine: ((String) -> Void)? = nil
    ) throws -> (exitCode: Int32, combinedOutput: String) {
        let process = Process()
        process.executableURL = executableURL
        process.arguments = buildArguments(arguments)
        if let workingDirectory {
            process.currentDirectoryURL = workingDirectory
        }

        let stdout = Pipe()
        let stderr = Pipe()
        process.standardOutput = stdout
        process.standardError = stderr

        try process.run()

        var chunks: [String] = []
        let outData = stdout.fileHandleForReading.readDataToEndOfFile()
        let errData = stderr.fileHandleForReading.readDataToEndOfFile()
        process.waitUntilExit()

        if let text = String(data: outData, encoding: .utf8), !text.isEmpty {
            chunks.append(text)
            text.split(separator: "\n", omittingEmptySubsequences: false).forEach {
                onOutputLine?(String($0))
            }
        }
        if let text = String(data: errData, encoding: .utf8), !text.isEmpty {
            chunks.append(text)
            text.split(separator: "\n", omittingEmptySubsequences: false).forEach {
                onOutputLine?(String($0))
            }
        }

        return (process.terminationStatus, chunks.joined())
    }

    private static func which(
        _ name: String,
        fileManager: FileManager
    ) -> URL? {
        let path = ProcessInfo.processInfo.environment["PATH"] ?? "/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin"
        for directory in path.split(separator: ":") {
            let candidate = URL(fileURLWithPath: String(directory)).appendingPathComponent(name)
            if fileManager.isExecutableFile(atPath: candidate.path) {
                return candidate
            }
        }
        return nil
    }
}
