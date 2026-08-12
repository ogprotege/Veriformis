import Foundation

/// Thin process adapter. Stage policy lives in Python `PipelineService` / CLI.
struct VeriformisCLI: Sendable {
    let executableURL: URL
    let prefixArguments: [String]

    /// Resolve the CLI: env override, PATH `veriformis`, or repo-local `uv run veriformis`.
    ///
    /// GUI apps inherit a minimal PATH (often without Homebrew or `~/.local/bin`).
    /// Resolution therefore also probes common install locations for `uv` and
    /// `veriformis`, and reads the Debug Info.plist repo root.
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

        if let pathCLI = findExecutable("veriformis", fileManager: fileManager) {
            return VeriformisCLI(executableURL: pathCLI, prefixArguments: [])
        }

        let root = repositoryRoot ?? developmentRepositoryRoot(fileManager: fileManager)
        if let root {
            let venvCLI = root.appendingPathComponent(".venv/bin/veriformis")
            if fileManager.isExecutableFile(atPath: venvCLI.path) {
                return VeriformisCLI(executableURL: venvCLI, prefixArguments: [])
            }
            if let uv = findExecutable("uv", fileManager: fileManager) {
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
            let url = URL(fileURLWithPath: env).standardizedFileURL
            if looksLikeRepoRoot(url, fileManager: fileManager) {
                return url
            }
        }
        if let builtIn = bundle.object(forInfoDictionaryKey: "VERIFORMIS_DEVELOPMENT_REPOSITORY_ROOT") as? String,
           !builtIn.isEmpty,
           !builtIn.hasPrefix("$(")
        {
            let url = URL(fileURLWithPath: builtIn).standardizedFileURL
            if looksLikeRepoRoot(url, fileManager: fileManager) {
                return url
            }
        }
        var dir = URL(fileURLWithPath: fileManager.currentDirectoryPath).standardizedFileURL
        for _ in 0 ..< 8 {
            if looksLikeRepoRoot(dir, fileManager: fileManager) {
                return dir
            }
            dir.deleteLastPathComponent()
        }
        var candidate = bundle.bundleURL.standardizedFileURL
        for _ in 0 ..< 12 {
            if looksLikeRepoRoot(candidate, fileManager: fileManager) {
                return candidate
            }
            let parent = candidate.deletingLastPathComponent()
            if parent.path == candidate.path { break }
            candidate = parent
        }
        return nil
    }

    static func resolutionDiagnostics(
        fileManager: FileManager = .default
    ) -> String {
        var lines: [String] = []
        let envCLI = ProcessInfo.processInfo.environment["VERIFORMIS_CLI"] ?? "(unset)"
        let envRoot = ProcessInfo.processInfo.environment["VERIFORMIS_DEVELOPMENT_REPOSITORY_ROOT"] ?? "(unset)"
        let plistRoot = Bundle.main.object(forInfoDictionaryKey: "VERIFORMIS_DEVELOPMENT_REPOSITORY_ROOT") as? String ?? "(missing)"
        lines.append("PATH=\(ProcessInfo.processInfo.environment["PATH"] ?? "(nil)")")
        lines.append("VERIFORMIS_CLI=\(envCLI)")
        lines.append("VERIFORMIS_DEVELOPMENT_REPOSITORY_ROOT=\(envRoot)")
        lines.append("Info.plist repo root=\(plistRoot)")
        lines.append("cwd=\(fileManager.currentDirectoryPath)")
        lines.append("bundle=\(Bundle.main.bundleURL.path)")
        if let root = developmentRepositoryRoot(fileManager: fileManager) {
            lines.append("resolved repo root=\(root.path)")
            let venv = root.appendingPathComponent(".venv/bin/veriformis")
            lines.append(
                "venv CLI exists=\(fileManager.fileExists(atPath: venv.path)) executable=\(fileManager.isExecutableFile(atPath: venv.path)) path=\(venv.path)"
            )
        } else {
            lines.append("resolved repo root=(nil)")
        }
        for name in ["veriformis", "uv"] {
            if let url = findExecutable(name, fileManager: fileManager) {
                lines.append("found \(name)=\(url.path)")
            } else {
                lines.append("found \(name)=(nil)")
            }
        }
        return lines.joined(separator: "\n")
    }

    func buildArguments(_ stageArguments: [String]) -> [String] {
        prefixArguments + stageArguments
    }

    static func compilePlan(
        sources: [URL],
        sourceRoot: URL,
        workspace: URL,
        bundle: URL,
        objective: TrainingObjective,
        allowEmptyEvaluation: Bool,
        splitRatioPPM: Int,
        includeHandoff: Bool = false
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
        if includeHandoff {
            sealArgs.append("--aptus-handoff")
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

        let stream = LineStream(onLine: onOutputLine)
        stdout.fileHandleForReading.readabilityHandler = { handle in
            let data = handle.availableData
            guard !data.isEmpty else { return }
            stream.append(data)
        }
        stderr.fileHandleForReading.readabilityHandler = { handle in
            let data = handle.availableData
            guard !data.isEmpty else { return }
            stream.append(data)
        }

        try process.run()
        process.waitUntilExit()

        stdout.fileHandleForReading.readabilityHandler = nil
        stderr.fileHandleForReading.readabilityHandler = nil
        stream.flushRemainder()

        return (process.terminationStatus, stream.combinedOutput)
    }

    private static func looksLikeRepoRoot(_ url: URL, fileManager: FileManager) -> Bool {
        let pyproject = url.appendingPathComponent("pyproject.toml")
        let src = url.appendingPathComponent("src/veriformis")
        return fileManager.fileExists(atPath: pyproject.path)
            && fileManager.fileExists(atPath: src.path)
    }

    private static func findExecutable(
        _ name: String,
        fileManager: FileManager
    ) -> URL? {
        if let fromPath = which(name, fileManager: fileManager) {
            return fromPath
        }
        let home = fileManager.homeDirectoryForCurrentUser.path
        let candidates: [String] = [
            "\(home)/.local/bin/\(name)",
            "\(home)/.cargo/bin/\(name)",
            "/opt/homebrew/bin/\(name)",
            "/usr/local/bin/\(name)",
            "/opt/local/bin/\(name)",
        ]
        for path in candidates {
            if fileManager.isExecutableFile(atPath: path) {
                return URL(fileURLWithPath: path)
            }
        }
        return nil
    }

    private static func which(
        _ name: String,
        fileManager: FileManager
    ) -> URL? {
        let path = ProcessInfo.processInfo.environment["PATH"]
            ?? "/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:/usr/local/bin"
        for directory in path.split(separator: ":") {
            let candidate = URL(fileURLWithPath: String(directory)).appendingPathComponent(name)
            if fileManager.isExecutableFile(atPath: candidate.path) {
                return candidate
            }
        }
        return nil
    }
}

/// Thread-safe line splitter for live process output.
private final class LineStream: @unchecked Sendable {
    private let lock = NSLock()
    private var buffer = Data()
    private var chunks: [String] = []
    private let onLine: ((String) -> Void)?

    init(onLine: ((String) -> Void)?) {
        self.onLine = onLine
    }

    var combinedOutput: String {
        lock.lock()
        defer { lock.unlock() }
        return chunks.joined()
    }

    func append(_ data: Data) {
        lock.lock()
        buffer.append(data)
        while let range = buffer.range(of: Data([0x0A])) {
            let lineData = buffer.subdata(in: buffer.startIndex ..< range.lowerBound)
            buffer.removeSubrange(buffer.startIndex ... range.lowerBound)
            if let line = String(data: lineData, encoding: .utf8) {
                chunks.append(line + "\n")
                let callback = onLine
                lock.unlock()
                callback?(line)
                lock.lock()
            }
        }
        lock.unlock()
    }

    func flushRemainder() {
        lock.lock()
        let remainder = buffer
        buffer.removeAll(keepingCapacity: false)
        guard !remainder.isEmpty, let line = String(data: remainder, encoding: .utf8) else {
            lock.unlock()
            return
        }
        chunks.append(line)
        let callback = onLine
        lock.unlock()
        callback?(line)
    }
}
