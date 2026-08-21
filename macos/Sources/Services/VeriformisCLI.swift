import Darwin
import Foundation

struct CLIProcessCancellation: Equatable, Sendable {
    let processIdentifier: Int32?
    let terminationStatus: Int32?
    let terminationEscalated: Bool
}

struct CLIProcessResult: Equatable, Sendable {
    let exitCode: Int32
    let combinedOutput: String
    let outputTruncated: Bool
    let cancellation: CLIProcessCancellation?
}

enum CLIProcessError: LocalizedError, Equatable {
    case alreadyRunning

    var errorDescription: String? {
        switch self {
        case .alreadyRunning:
            return "A Veriformis child process is already running."
        }
    }
}

/// Owns at most one child process and provides cooperative TERM → KILL cancellation.
final class CLIProcessController: @unchecked Sendable {
    private let lock = NSLock()
    private let terminationGrace: TimeInterval
    fileprivate let maxRetainedOutputBytes: Int
    private var activeExecution: CLIProcessExecution?

    init(
        terminationGrace: TimeInterval = 1.0,
        maxRetainedOutputBytes: Int = 2 * 1024 * 1024
    ) {
        self.terminationGrace = max(0, terminationGrace)
        self.maxRetainedOutputBytes = max(1_024, maxRetainedOutputBytes)
    }

    var hasActiveProcess: Bool {
        lock.withLock { activeExecution != nil }
    }

    func cancel() {
        let execution = lock.withLock { activeExecution }
        execution?.cancel()
    }

    fileprivate func execute(
        executableURL: URL,
        arguments: [String],
        workingDirectory: URL?,
        onOutputLine: (@Sendable (String) -> Void)?
    ) async throws -> CLIProcessResult {
        let execution = CLIProcessExecution(
            executableURL: executableURL,
            arguments: arguments,
            workingDirectory: workingDirectory,
            terminationGrace: terminationGrace,
            maxRetainedOutputBytes: maxRetainedOutputBytes,
            onOutputLine: onOutputLine
        )
        try lock.withLock {
            guard activeExecution == nil else { throw CLIProcessError.alreadyRunning }
            activeExecution = execution
        }
        defer {
            lock.withLock {
                if activeExecution === execution {
                    activeExecution = nil
                }
            }
        }
        return try await withTaskCancellationHandler {
            try await execution.start()
        } onCancel: {
            execution.cancel()
        }
    }
}

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
        fileManager: FileManager = .default,
        environment: [String: String] = ProcessInfo.processInfo.environment
    ) throws -> VeriformisCLI {
        if let override = environment["VERIFORMIS_CLI"], !override.isEmpty {
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
        if includeHandoff {
            constructArgs.append(contentsOf: ["--consumer-profile", "aptus-handoff-v1"])
        }
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
        controller: CLIProcessController = CLIProcessController(),
        onOutputLine: (@Sendable (String) -> Void)? = nil
    ) async throws -> CLIProcessResult {
        try await controller.execute(
            executableURL: executableURL,
            arguments: buildArguments(arguments),
            workingDirectory: workingDirectory,
            onOutputLine: onOutputLine
        )
    }

    /// Load the implemented taxonomy from the CLI without blocking the main actor.
    func discoverTaxonomy(
        controller: CLIProcessController = CLIProcessController()
    ) async throws -> TaxonomyDiscovery {
        let result = try await run(
            arguments: ["taxonomy"],
            controller: controller
        )
        if result.cancellation != nil || Task.isCancelled {
            throw CancellationError()
        }
        guard result.exitCode == 0 else {
            throw TaxonomyDiscoveryError.commandFailed(
                exitCode: result.exitCode,
                message: result.combinedOutput.trimmingCharacters(in: .whitespacesAndNewlines)
            )
        }
        guard !result.outputTruncated else {
            throw TaxonomyDiscoveryError.outputTruncated
        }
        do {
            return try JSONDecoder().decode(
                TaxonomyDiscovery.self,
                from: Data(result.combinedOutput.utf8)
            )
        } catch let error as TaxonomyDiscoveryError {
            throw error
        } catch {
            throw TaxonomyDiscoveryError.invalidPayload(error.localizedDescription)
        }
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

/// One asynchronous process execution. Launch and completion never run on the main actor.
private final class CLIProcessExecution: @unchecked Sendable {
    private let process = Process()
    private let stdout = Pipe()
    private let stderr = Pipe()
    private let stream: BoundedLineStream
    private let terminationGrace: TimeInterval
    private let lock = NSLock()
    private var continuation: CheckedContinuation<CLIProcessResult, Error>?
    private var cancelRequested = false
    private var terminationRequested = false
    private var terminationEscalated = false
    private var launchedPID: Int32?
    private var finished = false

    init(
        executableURL: URL,
        arguments: [String],
        workingDirectory: URL?,
        terminationGrace: TimeInterval,
        maxRetainedOutputBytes: Int,
        onOutputLine: (@Sendable (String) -> Void)?
    ) {
        self.terminationGrace = terminationGrace
        stream = BoundedLineStream(
            maxRetainedBytes: maxRetainedOutputBytes,
            onLine: onOutputLine
        )
        process.executableURL = executableURL
        process.arguments = arguments
        process.currentDirectoryURL = workingDirectory
        process.standardOutput = stdout
        process.standardError = stderr
    }

    func start() async throws -> CLIProcessResult {
        try await withCheckedThrowingContinuation { continuation in
            DispatchQueue.global(qos: .userInitiated).async { [self] in
                launch(continuation)
            }
        }
    }

    func cancel() {
        let shouldTerminate = lock.withLock { () -> Bool in
            cancelRequested = true
            return launchedPID != nil && !finished
        }
        if shouldTerminate {
            requestTermination()
        }
    }

    private func launch(_ continuation: CheckedContinuation<CLIProcessResult, Error>) {
        let cancelledBeforeLaunch = lock.withLock { () -> Bool in
            self.continuation = continuation
            if cancelRequested {
                finished = true
                self.continuation = nil
                return true
            }
            return false
        }
        if cancelledBeforeLaunch {
            continuation.resume(returning: CLIProcessResult(
                exitCode: -1,
                combinedOutput: "",
                outputTruncated: false,
                cancellation: CLIProcessCancellation(
                    processIdentifier: nil,
                    terminationStatus: nil,
                    terminationEscalated: false
                )
            ))
            return
        }

        stdout.fileHandleForReading.readabilityHandler = { [stream] handle in
            let data = handle.availableData
            if !data.isEmpty { stream.append(data) }
        }
        stderr.fileHandleForReading.readabilityHandler = { [stream] handle in
            let data = handle.availableData
            if !data.isEmpty { stream.append(data) }
        }
        process.terminationHandler = { [weak self] process in
            self?.complete(process)
        }

        do {
            try process.run()
            let shouldTerminate = lock.withLock { () -> Bool in
                launchedPID = process.processIdentifier
                return cancelRequested
            }
            if shouldTerminate {
                requestTermination()
            }
        } catch {
            finishLaunchFailure(error)
        }
    }

    private func requestTermination() {
        let shouldRequest = lock.withLock { () -> Bool in
            guard !terminationRequested, !finished else { return false }
            terminationRequested = true
            return true
        }
        guard shouldRequest else { return }
        if process.isRunning {
            process.terminate()
        }
        DispatchQueue.global(qos: .userInitiated).asyncAfter(
            deadline: .now() + terminationGrace
        ) { [weak self] in
            self?.forceTerminateIfNeeded()
        }
    }

    private func forceTerminateIfNeeded() {
        let pid = lock.withLock { () -> Int32? in
            guard cancelRequested, !finished, process.isRunning,
                  let launchedPID
            else {
                return nil
            }
            terminationEscalated = true
            return launchedPID
        }
        if let pid {
            _ = Darwin.kill(pid, SIGKILL)
        }
    }

    private func complete(_ process: Process) {
        let completion = lock.withLock { () -> (
            CheckedContinuation<CLIProcessResult, Error>,
            Bool,
            Bool,
            Int32?
        )? in
            guard !finished, let continuation else { return nil }
            finished = true
            self.continuation = nil
            return (
                continuation,
                cancelRequested,
                terminationEscalated,
                launchedPID
            )
        }
        guard let (continuation, wasCancelled, escalated, pid) = completion else {
            return
        }

        stopReadingAndDrain()
        let snapshot = stream.snapshot()
        continuation.resume(returning: CLIProcessResult(
            exitCode: process.terminationStatus,
            combinedOutput: snapshot.output,
            outputTruncated: snapshot.truncated,
            cancellation: wasCancelled
                ? CLIProcessCancellation(
                    processIdentifier: pid,
                    terminationStatus: process.terminationStatus,
                    terminationEscalated: escalated
                )
                : nil
        ))
    }

    private func finishLaunchFailure(_ error: Error) {
        let continuation = lock.withLock { () -> CheckedContinuation<CLIProcessResult, Error>? in
            guard !finished else { return nil }
            finished = true
            let value = self.continuation
            self.continuation = nil
            return value
        }
        stdout.fileHandleForReading.readabilityHandler = nil
        stderr.fileHandleForReading.readabilityHandler = nil
        continuation?.resume(throwing: error)
    }

    private func stopReadingAndDrain() {
        stdout.fileHandleForReading.readabilityHandler = nil
        stderr.fileHandleForReading.readabilityHandler = nil
        let stdoutRemainder = stdout.fileHandleForReading.readDataToEndOfFile()
        let stderrRemainder = stderr.fileHandleForReading.readDataToEndOfFile()
        if !stdoutRemainder.isEmpty { stream.append(stdoutRemainder) }
        if !stderrRemainder.isEmpty { stream.append(stderrRemainder) }
        stream.flushRemainder()
    }
}

/// Thread-safe, lossy-UTF-8 line splitter with bounded retained output.
private final class BoundedLineStream: @unchecked Sendable {
    private let lock = NSLock()
    private var buffer = Data()
    private var chunks: [Data] = []
    private var retainedBytes = 0
    private var wasTruncated = false
    private let maxRetainedBytes: Int
    private let onLine: (@Sendable (String) -> Void)?

    init(
        maxRetainedBytes: Int,
        onLine: (@Sendable (String) -> Void)?
    ) {
        self.maxRetainedBytes = maxRetainedBytes
        self.onLine = onLine
    }

    func snapshot() -> (output: String, truncated: Bool) {
        lock.withLock {
            var data = chunks.reduce(into: Data()) { result, chunk in
                result.append(chunk)
            }
            if wasTruncated {
                let marker = Data("[... earlier process output truncated ...]\n".utf8)
                let allowed = max(0, maxRetainedBytes - marker.count)
                data = marker + data.suffix(allowed)
            }
            return (String(decoding: data, as: UTF8.self), wasTruncated)
        }
    }

    func append(_ data: Data) {
        var delivered: [String] = []
        lock.withLock {
            buffer.append(data)
            while let range = buffer.range(of: Data([0x0A])) {
                let lineData = buffer.subdata(in: buffer.startIndex ..< range.lowerBound)
                let completeLine = buffer.subdata(in: buffer.startIndex ..< range.upperBound)
                buffer.removeSubrange(buffer.startIndex ..< range.upperBound)
                retain(completeLine)
                delivered.append(String(decoding: lineData, as: UTF8.self))
            }
            if buffer.count > maxRetainedBytes {
                let fragment = buffer
                buffer.removeAll(keepingCapacity: true)
                retain(fragment)
                delivered.append(String(decoding: fragment, as: UTF8.self))
            }
        }
        let callback = onLine
        for line in delivered { callback?(line) }
    }

    func flushRemainder() {
        let line: String? = lock.withLock {
            guard !buffer.isEmpty else { return nil }
            let remainder = buffer
            buffer.removeAll(keepingCapacity: false)
            retain(remainder)
            return String(decoding: remainder, as: UTF8.self)
        }
        if let line {
            onLine?(line)
        }
    }

    private func retain(_ data: Data) {
        chunks.append(data)
        retainedBytes += data.count
        while retainedBytes > maxRetainedBytes, !chunks.isEmpty {
            let overflow = retainedBytes - maxRetainedBytes
            if overflow >= chunks[0].count {
                retainedBytes -= chunks.removeFirst().count
            } else {
                chunks[0].removeFirst(overflow)
                retainedBytes -= overflow
            }
            wasTruncated = true
        }
    }
}

private extension NSLock {
    func withLock<T>(_ body: () throws -> T) rethrows -> T {
        lock()
        defer { unlock() }
        return try body()
    }
}
