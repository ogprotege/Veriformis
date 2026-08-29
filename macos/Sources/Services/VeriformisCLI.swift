import Darwin
import CoreFoundation
import Foundation

struct CLIProcessCancellation: Equatable, Sendable {
    let processIdentifier: Int32?
    let terminationStatus: Int32?
    let terminationEscalated: Bool
}

struct CLIProcessResult: Equatable, Sendable {
    let exitCode: Int32
    let standardOutputData: Data
    let standardErrorData: Data
    let standardOutput: String
    let standardError: String
    let standardOutputTruncated: Bool
    let standardErrorTruncated: Bool
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

enum ExportCLIBridgeError: LocalizedError, Equatable, Sendable {
    case outputTruncated(operation: ExportOperation)
    case forcedTermination(operation: ExportOperation)
    case cancelledWithoutResponse(operation: ExportOperation)
    case commandFailed(operation: ExportOperation, exitCode: Int32, message: String)
    case invalidResponse(operation: ExportOperation, message: String)
    case inconsistentExitStatus(
        operation: ExportOperation,
        status: ExportResponseStatus,
        exitCode: Int32
    )

    var errorDescription: String? {
        switch self {
        case .outputTruncated(let operation):
            return "Export \(operation.rawValue) output was truncated; no response was accepted."
        case .forcedTermination(let operation):
            return "Export \(operation.rawValue) was force-terminated; destination state is ambiguous and must be inspected or verified."
        case .cancelledWithoutResponse(let operation):
            return "Export \(operation.rawValue) was cancelled without a complete authoritative response."
        case .commandFailed(let operation, let exitCode, let message):
            let detail = message.isEmpty ? "No diagnostic was returned." : message
            return "Export \(operation.rawValue) failed (exit \(exitCode)): \(detail)"
        case .invalidResponse(let operation, let message):
            return "Export \(operation.rawValue) returned an invalid response: \(message)"
        case .inconsistentExitStatus(let operation, let status, let exitCode):
            return "Export \(operation.rawValue) returned status \(status.rawValue) with inconsistent exit \(exitCode)."
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

    /// The goal-first compile sequence. Every recipe default comes from the
    /// CLI's versioned preset data: the workbench passes only the selection
    /// (goal and preset) and explicit operator overrides.
    ///
    /// `document-source` omits `--mode` (ADR-0010 default). `dataset-row` and
    /// mixed-with-rows run parse, map, then the finished-dataset tail. Mixed
    /// document-only keeps the document-source tail with `--mode mixed`.
    static func compilePlan(
        sources: [URL],
        sourceRoot: URL,
        workspace: URL,
        bundle: URL,
        goal: String,
        preset: String,
        allowEmptyEvaluation: Bool,
        splitRatioPPM: Int?,
        representation: String? = nil,
        instruction: String? = nil,
        cleaningRules: String = "",
        cleaningCustom: String = "",
        chunkSize: Int? = nil,
        chunkOverlap: Int? = nil,
        includeHandoff: Bool = false,
        mode: CompilerInputMode = .documentSource,
        mappingPlanURL: URL? = nil
    ) -> [StageCommand] {
        var parseArgs = ["parse"]
        parseArgs.append(contentsOf: sources.map(\.path))
        parseArgs.append(contentsOf: ["-o", workspace.path, "--source-root", sourceRoot.path])
        if mode != .documentSource {
            parseArgs.append(contentsOf: ["--mode", mode.rawValue])
        }

        var curateArgs = ["curate", workspace.path, "--preset", preset]
        if let instruction {
            curateArgs.append(contentsOf: ["--instruction", instruction])
        }
        if allowEmptyEvaluation {
            curateArgs.append("--allow-empty-evaluation")
        }

        var sealArgs = ["seal", workspace.path, "-o", bundle.path]
        if includeHandoff {
            sealArgs.append("--aptus-handoff")
        }

        let finishedTail: [StageCommand] = [
            StageCommand(stage: .curate, arguments: curateArgs),
            StageCommand(stage: .split, arguments: ["split", workspace.path]),
            StageCommand(stage: .format, arguments: ["format", workspace.path]),
            StageCommand(stage: .validate, arguments: ["validate", workspace.path]),
            StageCommand(stage: .seal, arguments: sealArgs),
        ]

        let includesMapping = mappingPlanURL != nil && (mode == .datasetRow || mode == .mixed)
        if includesMapping, let mappingPlanURL {
            var mapArgs = ["map", workspace.path, "--goal", goal]
            if let representation {
                mapArgs.append(contentsOf: ["--representation", representation])
            }
            mapArgs.append(contentsOf: ["--plan", mappingPlanURL.path])
            return [
                StageCommand(stage: .parse, arguments: parseArgs),
                StageCommand(stage: .map, arguments: mapArgs),
            ] + finishedTail
        }

        var cleanArgs = ["clean", workspace.path]
        if !cleaningRules.isEmpty {
            cleanArgs.append(contentsOf: ["--rules", cleaningRules])
        }
        if !cleaningCustom.isEmpty {
            cleanArgs.append(contentsOf: ["--custom", cleaningCustom])
        }

        let hasSegmentationOverride = chunkSize != nil || chunkOverlap != nil
        var chunkArgs = ["chunk", workspace.path, "--preset", preset]
        if let chunkSize {
            chunkArgs.append(contentsOf: ["--size", String(chunkSize)])
        }
        if let chunkOverlap {
            chunkArgs.append(contentsOf: ["--overlap", String(chunkOverlap)])
        }

        var constructArgs = ["construct", workspace.path, "--goal", goal]
        if !hasSegmentationOverride {
            constructArgs.append(contentsOf: ["--preset", preset])
        }
        if let representation {
            constructArgs.append(contentsOf: ["--representation", representation])
        }
        if includeHandoff {
            constructArgs.append(contentsOf: ["--consumer-profile", "aptus-handoff-v1"])
        }
        if let splitRatioPPM {
            constructArgs.append(contentsOf: ["--split-ratio-ppm", String(splitRatioPPM)])
        }

        return [
            StageCommand(stage: .parse, arguments: parseArgs),
            StageCommand(stage: .clean, arguments: cleanArgs),
            StageCommand(stage: .chunk, arguments: chunkArgs),
            StageCommand(stage: .construct, arguments: constructArgs),
        ] + finishedTail
    }

    /// Quote one argv token for a copyable shell equivalent.
    static func shellQuote(_ value: String) -> String {
        let safe = CharacterSet.alphanumerics.union(CharacterSet(charactersIn: "-_./:@+,"))
        if !value.isEmpty, value.unicodeScalars.allSatisfy({ safe.contains($0) }) {
            return value
        }
        return "'" + value.replacingOccurrences(of: "'", with: "'\\''") + "'"
    }

    /// Exact CLI equivalent of a compile plan. Loading this string is not an execute.
    static func cliEquivalent(for plan: [StageCommand]) -> String {
        plan.map { command in
            "veriformis " + command.arguments.map(shellQuote).joined(separator: " ")
        }
        .joined(separator: " && \\\n")
    }

    /// Exact CLI argument projection for one runtime-only compile preflight.
    /// Omitted overrides leave the selected versioned preset authoritative.
    static func preflightArguments(_ request: CompilePreflightRequest) -> [String] {
        var arguments = ["preflight"]
        arguments.append(contentsOf: request.sources.map(\.path))
        arguments += [
            "--source-root", request.sourceRoot.path,
            "--goal", request.goal,
            "--preset", request.preset,
            "--representation", request.representation,
        ]
        if let instruction = request.instruction {
            arguments += ["--instruction", instruction]
        }
        if !request.rules.isEmpty {
            arguments += ["--rules", request.rules]
        }
        if !request.custom.isEmpty {
            arguments += ["--custom", request.custom]
        }
        if let strategy = request.strategy {
            arguments += ["--strategy", strategy]
        }
        if let size = request.size {
            arguments += ["--size", String(size)]
        }
        if let overlap = request.overlap {
            arguments += ["--overlap", String(overlap)]
        }
        if let splitRatioPPM = request.splitRatioPPM {
            arguments += ["--split-ratio-ppm", String(splitRatioPPM)]
        }
        if let requireReview = request.requireReview {
            arguments.append(requireReview ? "--require-review" : "--no-require-review")
        }
        if let consumerProfile = request.consumerProfile {
            arguments += ["--consumer-profile", consumerProfile]
        }
        if let minimumTargetCharacters = request.minimumTargetCharacters {
            arguments += ["--minimum-target-characters", String(minimumTargetCharacters)]
        }
        if let balanceMode = request.balanceMode {
            arguments += ["--balance-mode", balanceMode]
        }
        if let maximumRecordsPerPrimarySource = request.maximumRecordsPerPrimarySource {
            arguments += [
                "--maximum-records-per-primary-source",
                String(maximumRecordsPerPrimarySource),
            ]
        }
        if let evaluationRatioPPM = request.evaluationRatioPPM {
            arguments += ["--evaluation-ratio-ppm", String(evaluationRatioPPM)]
        }
        if let evaluationRequired = request.evaluationRequired {
            arguments.append(evaluationRequired ? "--require-evaluation" : "--allow-empty-evaluation")
        }
        if let splitSeed = request.splitSeed {
            arguments += ["--split-seed", splitSeed]
        }
        if let reviewPolicy = request.reviewPolicy {
            arguments += ["--review-policy", reviewPolicy]
        }
        if request.mode != .documentSource {
            arguments += ["--mode", request.mode.rawValue]
        }
        return arguments
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
        guard !result.standardOutputTruncated else {
            throw TaxonomyDiscoveryError.outputTruncated
        }
        do {
            return try JSONDecoder().decode(
                TaxonomyDiscovery.self,
                from: result.standardOutputData
            )
        } catch let error as TaxonomyDiscoveryError {
            throw error
        } catch {
            throw TaxonomyDiscoveryError.invalidPayload(error.localizedDescription)
        }
    }

    /// Load the plain-language goal catalog from the CLI without blocking the main actor.
    func discoverGoals(
        controller: CLIProcessController = CLIProcessController()
    ) async throws -> GoalCatalog {
        let result = try await run(
            arguments: ["goals"],
            controller: controller
        )
        if result.cancellation != nil || Task.isCancelled {
            throw CancellationError()
        }
        guard result.exitCode == 0 else {
            throw GoalCatalogError.commandFailed(
                exitCode: result.exitCode,
                message: result.combinedOutput.trimmingCharacters(in: .whitespacesAndNewlines)
            )
        }
        guard !result.standardOutputTruncated else {
            throw GoalCatalogError.outputTruncated
        }
        do {
            return try JSONDecoder().decode(
                GoalCatalog.self,
                from: result.standardOutputData
            )
        } catch let error as GoalCatalogError {
            throw error
        } catch {
            throw GoalCatalogError.invalidPayload(error.localizedDescription)
        }
    }

    /// Load the versioned recipe presets and defaults from the CLI.
    func discoverPresets(
        controller: CLIProcessController = CLIProcessController()
    ) async throws -> RecipePresetCatalog {
        let result = try await run(arguments: ["presets"], controller: controller)
        if result.cancellation != nil || Task.isCancelled {
            throw CancellationError()
        }
        guard result.exitCode == 0 else {
            throw RecipePresetError.commandFailed(
                exitCode: result.exitCode,
                message: result.combinedOutput.trimmingCharacters(in: .whitespacesAndNewlines)
            )
        }
        guard !result.standardOutputTruncated else {
            throw RecipePresetError.outputTruncated
        }
        do {
            return try JSONDecoder().decode(RecipePresetCatalog.self, from: result.standardOutputData)
        } catch let error as RecipePresetError {
            throw error
        } catch {
            throw RecipePresetError.invalidPayload(error.localizedDescription)
        }
    }

    /// Propose mapping plans for one JSONL file without writing a workspace.
    /// Passing a goal or representation only filters detectors; it is not confirm.
    func detectMapping(
        path: String,
        sourceRoot: String? = nil,
        goal: String? = nil,
        representation: String? = nil,
        controller: CLIProcessController = CLIProcessController()
    ) async throws -> MappingDetectResponse {
        var arguments = ["mapping-detect", path]
        if let sourceRoot {
            arguments += ["--source-root", sourceRoot]
        }
        if let goal {
            arguments += ["--goal", goal]
        }
        if let representation {
            arguments += ["--representation", representation]
        }
        let result = try await run(arguments: arguments, controller: controller)
        if result.cancellation != nil || Task.isCancelled {
            throw CancellationError()
        }
        guard !result.standardOutputTruncated else {
            throw MappingDetectError.outputTruncated
        }
        do {
            return try JSONDecoder().decode(
                MappingDetectResponse.self,
                from: result.standardOutputData
            )
        } catch let error as MappingDetectError {
            throw error
        } catch {
            throw MappingDetectError.invalidPayload(error.localizedDescription)
        }
    }

    /// Preview a confirmed mapping plan across one file without writing a workspace.
    func previewMapping(
        path: String,
        planURL: URL,
        sourceRoot: String? = nil,
        controller: CLIProcessController = CLIProcessController()
    ) async throws -> MappingPreview {
        var arguments = ["mapping-preview", path, "--plan", planURL.path]
        if let sourceRoot {
            arguments += ["--source-root", sourceRoot]
        }
        let result = try await run(arguments: arguments, controller: controller)
        if result.cancellation != nil || Task.isCancelled {
            throw CancellationError()
        }
        guard !result.standardOutputTruncated else {
            throw MappingPreviewError.outputTruncated
        }
        guard result.exitCode == 0 else {
            throw MappingPreviewError.commandFailed(
                exitCode: result.exitCode,
                message: result.combinedOutput.trimmingCharacters(in: .whitespacesAndNewlines)
            )
        }
        do {
            return try JSONDecoder().decode(
                MappingPreview.self,
                from: result.standardOutputData
            )
        } catch let error as MappingPreviewError {
            throw error
        } catch {
            throw MappingPreviewError.invalidPayload(error.localizedDescription)
        }
    }

    /// Inspect raw sources and the complete resolved recipe before a workspace exists.
    /// Exit 0 is admitted and exit 2 is a complete, ordinary refusal response.
    func preflight(
        _ request: CompilePreflightRequest,
        controller: CLIProcessController = CLIProcessController()
    ) async throws -> CompilePreflight {
        let result = try await run(
            arguments: Self.preflightArguments(request),
            controller: controller
        )
        if result.cancellation != nil || Task.isCancelled {
            throw CancellationError()
        }
        guard !result.standardOutputTruncated else {
            throw CompilePreflightError.outputTruncated
        }
        guard result.exitCode == 0 || result.exitCode == 2 else {
            throw CompilePreflightError.commandFailed(
                exitCode: result.exitCode,
                message: result.combinedOutput.trimmingCharacters(in: .whitespacesAndNewlines)
            )
        }
        let response: CompilePreflight
        do {
            response = try JSONDecoder().decode(
                CompilePreflight.self,
                from: result.standardOutputData
            )
        } catch let error as CompilePreflightError {
            throw error
        } catch {
            throw CompilePreflightError.invalidPayload(error.localizedDescription)
        }
        let expectedExit: Int32 = response.admitted ? 0 : 2
        guard result.exitCode == expectedExit else {
            throw CompilePreflightError.inconsistentExitStatus(
                exitCode: result.exitCode,
                admitted: response.admitted
            )
        }
        return response
    }

    /// Load the goal-specific preview for a constructed workspace without blocking the main actor.
    func previewGoal(
        workspace: URL,
        representation: String? = nil,
        instruction: String? = nil,
        controller: CLIProcessController = CLIProcessController()
    ) async throws -> GoalPreview {
        var arguments = ["goal-preview", workspace.path]
        if let representation {
            arguments += ["--representation", representation]
        }
        if let instruction {
            arguments += ["--instruction", instruction]
        }
        let result = try await run(arguments: arguments, controller: controller)
        if result.cancellation != nil || Task.isCancelled {
            throw CancellationError()
        }
        guard result.exitCode == 0 else {
            throw GoalPreviewError.commandFailed(
                exitCode: result.exitCode,
                message: result.combinedOutput.trimmingCharacters(in: .whitespacesAndNewlines)
            )
        }
        guard !result.standardOutputTruncated else {
            throw GoalPreviewError.outputTruncated
        }
        do {
            return try JSONDecoder().decode(GoalPreview.self, from: result.standardOutputData)
        } catch let error as GoalPreviewError {
            throw error
        } catch {
            throw GoalPreviewError.invalidPayload(error.localizedDescription)
        }
    }

    /// Discover only the export implementations registered by the Python composition root.
    func discoverExports(
        controller: CLIProcessController = CLIProcessController()
    ) async throws -> ExportSurfaceResponse<ExportDiscovery> {
        try await runExportCommand(
            operation: .discover,
            arguments: ["export", "discover"],
            controller: controller
        )
    }

    func dryRunExport(
        _ request: ExportDryRunRequest,
        controller: CLIProcessController = CLIProcessController()
    ) async throws -> ExportSurfaceResponse<ExportDryRunResult> {
        try await runExportCommand(
            operation: .dryRun,
            arguments: ["export", "dry-run", "--request-json", try request.canonicalJSON()],
            controller: controller
        )
    }

    func dryRunExport(
        _ request: ExportDryRunRequestV2,
        controller: CLIProcessController = CLIProcessController()
    ) async throws -> ExportSurfaceResponse<ExportDryRunResult> {
        try await runExportCommand(
            operation: .dryRun,
            arguments: ["export", "dry-run", "--request-json", try request.canonicalJSON()],
            controller: controller
        )
    }

    func inspectExport(
        _ request: ExportInspectRequest,
        controller: CLIProcessController = CLIProcessController()
    ) async throws -> ExportSurfaceResponse<ExportInspectionResult> {
        try await runExportCommand(
            operation: .inspect,
            arguments: ["export", "inspect", "--request-json", try request.canonicalJSON()],
            controller: controller
        )
    }

    func executeExport(
        _ request: ExportExecuteRequest,
        controller: CLIProcessController = CLIProcessController()
    ) async throws -> ExportSurfaceResponse<ExportExecutionResult> {
        try await runExportCommand(
            operation: .execute,
            arguments: ["export", "execute", "--request-json", try request.canonicalJSON()],
            controller: controller
        )
    }

    func executeExport(
        _ request: ExportExecuteRequestV2,
        controller: CLIProcessController = CLIProcessController()
    ) async throws -> ExportSurfaceResponse<ExportExecutionResult> {
        try await runExportCommand(
            operation: .execute,
            arguments: ["export", "execute", "--request-json", try request.canonicalJSON()],
            controller: controller
        )
    }

    func verifyExport(
        _ request: ExportVerifyRequest,
        controller: CLIProcessController = CLIProcessController()
    ) async throws -> ExportSurfaceResponse<ExportVerifyResult> {
        try await runExportCommand(
            operation: .verify,
            arguments: ["export-verify", "--request-json", try request.canonicalJSON()],
            controller: controller
        )
    }

    func verifyExport(
        _ request: ExportVerifyRequestV2,
        controller: CLIProcessController = CLIProcessController()
    ) async throws -> ExportSurfaceResponse<ExportVerifyResult> {
        try await runExportCommand(
            operation: .verify,
            arguments: ["export-verify", "--request-json", try request.canonicalJSON()],
            controller: controller
        )
    }

    private func runExportCommand<Result: ExportSurfaceResult>(
        operation: ExportOperation,
        arguments: [String],
        controller: CLIProcessController
    ) async throws -> ExportSurfaceResponse<Result> {
        let processResult = try await run(
            arguments: arguments,
            controller: controller
        )
        guard !processResult.standardOutputTruncated else {
            if processResult.cancellation?.terminationEscalated == true {
                throw ExportCLIBridgeError.forcedTermination(operation: operation)
            }
            throw ExportCLIBridgeError.outputTruncated(operation: operation)
        }

        let response: ExportSurfaceResponse<Result>
        do {
            let responseData = try Self.canonicalExportResponseData(
                from: processResult.standardOutputData,
                operation: operation
            )
            response = try JSONDecoder().decode(
                ExportSurfaceResponse<Result>.self,
                from: responseData
            )
        } catch {
            if processResult.cancellation?.terminationEscalated == true {
                throw ExportCLIBridgeError.forcedTermination(operation: operation)
            }
            if processResult.cancellation != nil {
                throw ExportCLIBridgeError.cancelledWithoutResponse(operation: operation)
            }
            let diagnostic = processResult.standardError
                .trimmingCharacters(in: .whitespacesAndNewlines)
            if processResult.exitCode != 0, !diagnostic.isEmpty {
                throw ExportCLIBridgeError.commandFailed(
                    operation: operation,
                    exitCode: processResult.exitCode,
                    message: diagnostic
                )
            }
            throw ExportCLIBridgeError.invalidResponse(
                operation: operation,
                message: error.localizedDescription
            )
        }

        if let cancellation = processResult.cancellation {
            // Completed success/visibility evidence is authoritative even when
            // cancellation raced process exit. A preprinted failure does not
            // close publication state after SIGKILL.
            if response.status == .ok || response.status == .visiblePartial {
                return response
            }
            if cancellation.terminationEscalated {
                throw ExportCLIBridgeError.forcedTermination(operation: operation)
            }
        }
        guard Self.exitCode(processResult.exitCode, agreesWith: response.status) else {
            throw ExportCLIBridgeError.inconsistentExitStatus(
                operation: operation,
                status: response.status,
                exitCode: processResult.exitCode
            )
        }
        return response
    }

    private static func canonicalExportResponseData(
        from output: Data,
        operation: ExportOperation
    ) throws -> Data {
        var received = output
        if received.last == 0x0A {
            received.removeLast()
        }
        guard !received.isEmpty else {
            throw ExportSurfaceModelError.invalidValue("Export response stdout was empty.")
        }
        guard received.count <= 1024 * 1024 else {
            throw ExportSurfaceModelError.invalidValue(
                "Export response exceeds the 1 MiB surface limit."
            )
        }
        if operation == .dryRun, received.count > 256 * 1024 {
            throw ExportSurfaceModelError.invalidValue(
                "Export dry-run response exceeds the 256 KiB preview limit."
            )
        }
        let object = try JSONSerialization.jsonObject(with: received)
        guard JSONSerialization.isValidJSONObject(object) else {
            throw ExportSurfaceModelError.invalidValue("Export response was not a JSON object.")
        }
        let responseSchema = (object as? [String: Any])?["schema_version"] as? String
        let canonical: Data
        if responseSchema == ExportSurfaceSchema.responseV2 {
            canonical = try canonicalASCIIExportResponseData(object)
        } else {
            canonical = try JSONSerialization.data(
                withJSONObject: object,
                options: [.sortedKeys, .withoutEscapingSlashes]
            )
        }
        guard canonical == received else {
            throw ExportSurfaceModelError.invalidValue(
                "Export response stdout was not one canonical JSON object."
            )
        }
        return received
    }

    private static func canonicalASCIIExportResponseData(_ value: Any) throws -> Data {
        var result = ""
        try appendCanonicalASCIIExportJSON(value, to: &result, depth: 0)
        guard let data = result.data(using: .ascii) else {
            throw ExportSurfaceModelError.invalidValue(
                "Export response v2 could not be represented as canonical ASCII JSON."
            )
        }
        return data
    }

    private static func appendCanonicalASCIIExportJSON(
        _ value: Any,
        to result: inout String,
        depth: Int
    ) throws {
        guard depth <= 128 else {
            throw ExportSurfaceModelError.invalidValue(
                "Export response v2 exceeds the maximum JSON nesting depth."
            )
        }
        switch value {
        case is NSNull:
            result += "null"
        case let value as String:
            appendCanonicalASCIIExportJSONString(value, to: &result)
        case let value as NSNumber:
            if CFGetTypeID(value) == CFBooleanGetTypeID() {
                result += value.boolValue ? "true" : "false"
                return
            }
            let numberType = String(cString: value.objCType)
            guard numberType != "f", numberType != "d",
                  value.stringValue.range(
                      of: "^-?(0|[1-9][0-9]*)$",
                      options: .regularExpression
                  ) != nil
            else {
                throw ExportSurfaceModelError.invalidValue(
                    "Export response v2 contains a noncanonical number."
                )
            }
            result += value.stringValue
        case let value as [Any]:
            result += "["
            for (index, item) in value.enumerated() {
                if index > 0 { result += "," }
                try appendCanonicalASCIIExportJSON(
                    item,
                    to: &result,
                    depth: depth + 1
                )
            }
            result += "]"
        case let value as [String: Any]:
            result += "{"
            let keys = value.keys.sorted(by: exportJSONUnicodeScalarOrder)
            for (index, key) in keys.enumerated() {
                if index > 0 { result += "," }
                appendCanonicalASCIIExportJSONString(key, to: &result)
                result += ":"
                guard let item = value[key] else {
                    throw ExportSurfaceModelError.invalidValue(
                        "Export response v2 contains an unavailable object member."
                    )
                }
                try appendCanonicalASCIIExportJSON(
                    item,
                    to: &result,
                    depth: depth + 1
                )
            }
            result += "}"
        default:
            throw ExportSurfaceModelError.invalidValue(
                "Export response v2 contains an unsupported JSON value."
            )
        }
    }

    private static func appendCanonicalASCIIExportJSONString(
        _ value: String,
        to result: inout String
    ) {
        result += "\""
        for scalar in value.unicodeScalars {
            switch scalar.value {
            case 0x08:
                result += "\\b"
            case 0x09:
                result += "\\t"
            case 0x0A:
                result += "\\n"
            case 0x0C:
                result += "\\f"
            case 0x0D:
                result += "\\r"
            case 0x22:
                result += "\\\""
            case 0x5C:
                result += "\\\\"
            case 0x20 ... 0x7E:
                result.unicodeScalars.append(scalar)
            case 0 ... 0xFFFF:
                result += String(format: "\\u%04x", scalar.value)
            default:
                let supplementary = scalar.value - 0x1_0000
                let high = 0xD800 + (supplementary >> 10)
                let low = 0xDC00 + (supplementary & 0x3FF)
                result += String(format: "\\u%04x\\u%04x", high, low)
            }
        }
        result += "\""
    }

    private static func exportJSONUnicodeScalarOrder(_ lhs: String, _ rhs: String) -> Bool {
        let left = lhs.unicodeScalars.map(\.value)
        let right = rhs.unicodeScalars.map(\.value)
        for (leftValue, rightValue) in zip(left, right) where leftValue != rightValue {
            return leftValue < rightValue
        }
        return left.count < right.count
    }

    private static func exitCode(_ exitCode: Int32, agreesWith status: ExportResponseStatus) -> Bool {
        switch status {
        case .ok:
            return exitCode == 0
        case .error:
            return exitCode == 1 || exitCode == 2
        case .cancelled:
            return exitCode == 130
        case .visiblePartial:
            return exitCode == 1
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
    private let standardOutputStream: BoundedLineStream
    private let standardErrorStream: BoundedLineStream
    private let combinedStream: BoundedLineStream
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
        standardOutputStream = BoundedLineStream(
            maxRetainedBytes: maxRetainedOutputBytes,
            onLine: nil
        )
        standardErrorStream = BoundedLineStream(
            maxRetainedBytes: maxRetainedOutputBytes,
            onLine: nil
        )
        combinedStream = BoundedLineStream(
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
                standardOutputData: Data(),
                standardErrorData: Data(),
                standardOutput: "",
                standardError: "",
                standardOutputTruncated: false,
                standardErrorTruncated: false,
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

        stdout.fileHandleForReading.readabilityHandler = {
            [standardOutputStream, combinedStream] handle in
            let data = handle.availableData
            if !data.isEmpty {
                standardOutputStream.append(data)
                combinedStream.append(data)
            }
        }
        stderr.fileHandleForReading.readabilityHandler = {
            [standardErrorStream, combinedStream] handle in
            let data = handle.availableData
            if !data.isEmpty {
                standardErrorStream.append(data)
                combinedStream.append(data)
            }
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
        let standardOutputSnapshot = standardOutputStream.snapshot()
        let standardErrorSnapshot = standardErrorStream.snapshot()
        let combinedSnapshot = combinedStream.snapshot()
        continuation.resume(returning: CLIProcessResult(
            exitCode: process.terminationStatus,
            standardOutputData: standardOutputSnapshot.data,
            standardErrorData: standardErrorSnapshot.data,
            standardOutput: standardOutputSnapshot.output,
            standardError: standardErrorSnapshot.output,
            standardOutputTruncated: standardOutputSnapshot.truncated,
            standardErrorTruncated: standardErrorSnapshot.truncated,
            combinedOutput: combinedSnapshot.output,
            outputTruncated: combinedSnapshot.truncated,
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
        if !stdoutRemainder.isEmpty {
            standardOutputStream.append(stdoutRemainder)
            combinedStream.append(stdoutRemainder)
        }
        if !stderrRemainder.isEmpty {
            standardErrorStream.append(stderrRemainder)
            combinedStream.append(stderrRemainder)
        }
        standardOutputStream.flushRemainder()
        standardErrorStream.flushRemainder()
        combinedStream.flushRemainder()
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

    func snapshot() -> (data: Data, output: String, truncated: Bool) {
        lock.withLock {
            var data = chunks.reduce(into: Data()) { result, chunk in
                result.append(chunk)
            }
            if wasTruncated {
                let marker = Data("[... earlier process output truncated ...]\n".utf8)
                let allowed = max(0, maxRetainedBytes - marker.count)
                data = marker + data.suffix(allowed)
            }
            return (data, String(decoding: data, as: UTF8.self), wasTruncated)
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
