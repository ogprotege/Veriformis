import AppKit
import Foundation
import SwiftUI
import UniformTypeIdentifiers

@MainActor
final class WorkbenchViewModel: ObservableObject {
    nonisolated static let defaultWriteAptusHandoff = false
    /// Match the CLI curate default (`--require-evaluation`): fail closed when
    /// the evaluation partition would be empty. Empty-evaluation is an
    /// explicit per-run opt-in, never a silent GUI default.
    nonisolated static let defaultAllowEmptyEvaluation = false
    /// Match the CLI construct default for `--split-ratio-ppm`.
    nonisolated static let defaultSplitRatioPPM = 500_000

    // Navigation
    @Published var destination: SidebarDestination = .compile

    // Compile form
    @Published var sourceURLs: [URL] = []
    @Published var sourceRootURL: URL?
    private var userPinnedSourceRoot = false
    @Published var outputDirectoryURL: URL?
    @Published var objective: TrainingObjective = .fullText
    @Published var allowEmptyEvaluation = defaultAllowEmptyEvaluation
    @Published var splitRatioPPM = defaultSplitRatioPPM
    @Published var writeAptusHandoff = defaultWriteAptusHandoff
    @Published private(set) var taxonomyHelpState: TaxonomyHelpState = .idle
    @Published private(set) var goalPreviewState: GoalPreviewState = .idle

    // Run state
    @Published var isRunning = false
    @Published var showRunSheet = false
    @Published var currentStage: WorkbenchStage?
    @Published var completedStages: Set<WorkbenchStage> = []
    @Published var progressPercent: Double = 0
    @Published var logLines: [String] = []
    @Published var logExpanded = true
    @Published var lastError: String?
    @Published var lastFailure: CompileFailure?
    @Published var lastCancellation: RunCancellationReceipt?
    @Published var lastResult: CompileResult?
    @Published var lastCopiedNotice: String?
    @Published var runStatusMessage = "Ready"

    // History + settings
    @Published var runHistory: [RunHistoryEntry] = []
    @Published var selectedHistoryID: UUID?
    @Published var cliOverridePath: String = ""
    @Published var resolvedCLIDescription: String = "(not resolved)"
    @Published var defaultOutputPath: String = ""

    private var cli: VeriformisCLI?
    private let defaults: UserDefaults
    private let supportDirectoryOverride: URL?
    private let historyKey = "veriformis.workbench.runHistory.v1"
    private let defaultOutputKey = "veriformis.workbench.defaultOutput"
    private let cliOverrideKey = "veriformis.workbench.cliOverride"
    private let historyLimit = 100
    private var activeProcessController: CLIProcessController?
    private var compileTask: Task<Void, Never>?
    private var cancellationRequestedAt: Date?
    private var runFinishedCallbacks: [() -> Void] = []
    private var taxonomyHelpTask: Task<Void, Never>?
    private var taxonomyHelpController: CLIProcessController?
    private var goalPreviewTask: Task<Void, Never>?
    private var goalPreviewController: CLIProcessController?

    var canCompile: Bool {
        !isRunning
            && cli != nil
            && !sourceURLs.isEmpty
            && resolvedSourceRoot != nil
            && outputDirectoryURL != nil
    }

    var compileBlockedReason: String? {
        if isRunning { return "A compile is already running." }
        if cli == nil { return "CLI is not ready. Open Settings or relaunch via ./script/build_and_run.sh." }
        if sourceURLs.isEmpty { return "Add at least one source file." }
        if resolvedSourceRoot == nil { return "Source root directory is missing." }
        if outputDirectoryURL == nil { return "Choose an output folder (or set a default in Settings)." }
        return nil
    }

    var resolvedSourceRoot: URL? {
        sourceRootURL ?? Self.defaultSourceRoot(for: sourceURLs)
    }

    var selectedHistoryEntry: RunHistoryEntry? {
        guard let selectedHistoryID else { return runHistory.first }
        return runHistory.first { $0.id == selectedHistoryID }
    }

    init(
        cli: VeriformisCLI? = nil,
        defaults: UserDefaults = .standard,
        supportDirectory: URL? = nil
    ) {
        self.cli = cli
        self.defaults = defaults
        supportDirectoryOverride = supportDirectory
        if let cli {
            let prefix = cli.prefixArguments.isEmpty
                ? ""
                : " " + cli.prefixArguments.joined(separator: " ")
            resolvedCLIDescription = "\(cli.executableURL.path)\(prefix)"
            runStatusMessage = "CLI ready"
        }
        loadSettings()
        loadHistory()
        applyDefaultOutputIfNeeded()
    }

    func bootstrapCLI() {
        appendLog("Workbench bootstrap…")
        if !cliOverridePath.isEmpty {
            setenv("VERIFORMIS_CLI", cliOverridePath, 1)
        }
        appendLog(VeriformisCLI.resolutionDiagnostics())
        do {
            cli = try VeriformisCLI.resolve()
            let prefix = cli!.prefixArguments.isEmpty
                ? ""
                : " " + cli!.prefixArguments.joined(separator: " ")
            resolvedCLIDescription = "\(cli!.executableURL.path)\(prefix)"
            appendLog("CLI ready: \(resolvedCLIDescription)")
            runStatusMessage = "CLI ready"
            refreshTaxonomyHelp()
        } catch {
            cli = nil
            refreshTaxonomyHelp()
            resolvedCLIDescription = "(missing)"
            lastError = error.localizedDescription
            appendLog("error: \(error.localizedDescription)")
            appendLog("hint: use ./script/build_and_run.sh from the repo so the Debug app is rebuilt and opened.")
            runStatusMessage = "CLI missing"
        }
    }

    /// Cancel any stale request and replace it with discovery from the current CLI.
    /// Process execution suspends this main-actor task instead of blocking the UI.
    func refreshTaxonomyHelp() {
        taxonomyHelpTask?.cancel()
        taxonomyHelpController?.cancel()
        taxonomyHelpTask = nil
        taxonomyHelpController = nil

        guard let cli else {
            taxonomyHelpState = .unavailable("Veriformis CLI is unavailable.")
            return
        }

        let controller = CLIProcessController()
        taxonomyHelpController = controller
        taxonomyHelpState = .loading
        taxonomyHelpTask = Task { [weak self] in
            let nextState: TaxonomyHelpState
            do {
                let discovery = try await cli.discoverTaxonomy(controller: controller)
                try Task.checkCancellation()
                nextState = .ready(discovery)
            } catch is CancellationError {
                nextState = .unavailable("Taxonomy discovery was cancelled.")
            } catch {
                nextState = .unavailable(error.localizedDescription)
            }

            guard let self, self.taxonomyHelpController === controller else {
                return
            }
            self.taxonomyHelpState = nextState
            self.taxonomyHelpController = nil
            self.taxonomyHelpTask = nil
        }
    }

    /// Cancel any in-flight goal preview so a stale result cannot land later.
    func cancelGoalPreview() {
        goalPreviewTask?.cancel()
        goalPreviewController?.cancel()
        goalPreviewTask = nil
        goalPreviewController = nil
    }

    /// Load the goal-specific preview for one constructed workspace (Phase 6.3).
    func refreshGoalPreview(workspace: URL) {
        cancelGoalPreview()

        guard let cli else {
            goalPreviewState = .unavailable("Veriformis CLI is unavailable.")
            return
        }

        let controller = CLIProcessController()
        goalPreviewController = controller
        goalPreviewState = .loading
        goalPreviewTask = Task { [weak self] in
            let nextState: GoalPreviewState
            do {
                let preview = try await cli.previewGoal(workspace: workspace, controller: controller)
                try Task.checkCancellation()
                nextState = .ready(preview)
            } catch is CancellationError {
                nextState = .unavailable("Goal preview was cancelled.")
            } catch {
                nextState = .unavailable(error.localizedDescription)
            }

            guard let self, self.goalPreviewController === controller else {
                return
            }
            self.goalPreviewState = nextState
            self.goalPreviewController = nil
            self.goalPreviewTask = nil
        }
    }

    func addSources(_ urls: [URL]) {
        let existing = Set(sourceURLs.map(\.path))
        for url in urls where !existing.contains(url.path) {
            sourceURLs.append(url)
        }
        sourceURLs.sort { $0.path < $1.path }
        if sourceRootURL == nil || !userPinnedSourceRoot {
            sourceRootURL = Self.defaultSourceRoot(for: sourceURLs)
        }
    }

    func removeSource(_ url: URL) {
        sourceURLs.removeAll { $0.path == url.path }
        if !userPinnedSourceRoot {
            sourceRootURL = Self.defaultSourceRoot(for: sourceURLs)
        }
    }

    func clearSources() {
        sourceURLs = []
        lastResult = nil
        if !userPinnedSourceRoot {
            sourceRootURL = nil
        }
    }

    func chooseOutputDirectory() {
        let panel = NSOpenPanel()
        panel.canChooseFiles = false
        panel.canChooseDirectories = true
        panel.canCreateDirectories = true
        panel.prompt = "Choose Output Folder"
        if panel.runModal() == .OK, let url = panel.url {
            outputDirectoryURL = url
        }
    }

    func chooseDefaultOutputDirectory() {
        let panel = NSOpenPanel()
        panel.canChooseFiles = false
        panel.canChooseDirectories = true
        panel.canCreateDirectories = true
        panel.prompt = "Default Output Folder"
        if panel.runModal() == .OK, let url = panel.url {
            defaultOutputPath = url.path
            defaults.set(url.path, forKey: defaultOutputKey)
            if outputDirectoryURL == nil {
                outputDirectoryURL = url
            }
        }
    }

    func chooseSourceRoot() {
        let panel = NSOpenPanel()
        panel.canChooseFiles = false
        panel.canChooseDirectories = true
        panel.prompt = "Choose Source Root"
        if panel.runModal() == .OK, let url = panel.url {
            sourceRootURL = url.standardizedFileURL
            userPinnedSourceRoot = true
        }
    }

    func saveCLIOverride() {
        let trimmed = cliOverridePath.trimmingCharacters(in: .whitespacesAndNewlines)
        cliOverridePath = trimmed
        defaults.set(trimmed, forKey: cliOverrideKey)
        if trimmed.isEmpty {
            unsetenv("VERIFORMIS_CLI")
        } else {
            setenv("VERIFORMIS_CLI", trimmed, 1)
        }
        bootstrapCLI()
    }

    func clearCLIOverride() {
        cliOverridePath = ""
        defaults.removeObject(forKey: cliOverrideKey)
        unsetenv("VERIFORMIS_CLI")
        bootstrapCLI()
    }

    func compile() {
        guard !isRunning else { return }
        applyDefaultOutputIfNeeded()
        lastError = nil
        lastFailure = nil
        lastCancellation = nil
        lastResult = nil
        cancelGoalPreview()
        goalPreviewState = .idle
        lastCopiedNotice = nil
        completedStages = []
        currentStage = nil
        progressPercent = 0
        logLines = []
        logExpanded = true
        runStatusMessage = "Starting…"

        guard !sourceURLs.isEmpty else {
            lastError = WorkbenchError.noSources.localizedDescription
            return
        }
        guard let sourceRoot = resolvedSourceRoot else {
            lastError = WorkbenchError.invalidConfiguration("Source root is required.").localizedDescription
            return
        }
        guard let outputDirectory = outputDirectoryURL else {
            lastError = WorkbenchError.invalidConfiguration("Output folder is required.").localizedDescription
            return
        }
        guard cli != nil || (try? VeriformisCLI.resolve()) != nil else {
            lastError = WorkbenchError.missingCLI.localizedDescription
            return
        }

        isRunning = true
        showRunSheet = true
        let startedAt = Date()
        let sourcesSnapshot = sourceURLs
        let sourceRootSnapshot = sourceRoot
        let objectiveSnapshot = objective
        let allowEmptySnapshot = allowEmptyEvaluation
        let handoffSnapshot = writeAptusHandoff
        let splitSnapshot = splitRatioPPM
        let processController = CLIProcessController()
        activeProcessController = processController

        compileTask = Task {
            defer {
                isRunning = false
                activeProcessController = nil
                compileTask = nil
                cancellationRequestedAt = nil
                let callbacks = runFinishedCallbacks
                runFinishedCallbacks.removeAll()
                callbacks.forEach { $0() }
            }
            var combinedLog = ""
            var outputWasTruncated = false
            var workspace = outputDirectory
            var bundle = outputDirectory
            var transportArchive = outputDirectory
            var logFileURL: URL?
            do {
                let cli = try self.cli ?? VeriformisCLI.resolve()
                self.cli = cli

                let stamp = ISO8601DateFormatter().string(from: Date()).replacingOccurrences(of: ":", with: "-")
                workspace = outputDirectory.appendingPathComponent("workspace-\(stamp)", isDirectory: true)
                bundle = outputDirectory.appendingPathComponent("dataset-\(stamp).vfbundle", isDirectory: true)
                transportArchive = URL(fileURLWithPath: bundle.path + ".zip")
                try FileManager.default.createDirectory(at: workspace, withIntermediateDirectories: true)
                logFileURL = workspace.appendingPathComponent("run.log")

                let plan = VeriformisCLI.compilePlan(
                    sources: sourcesSnapshot,
                    sourceRoot: sourceRootSnapshot,
                    workspace: workspace,
                    bundle: bundle,
                    objective: objectiveSnapshot,
                    allowEmptyEvaluation: allowEmptySnapshot,
                    splitRatioPPM: splitSnapshot,
                    includeHandoff: handoffSnapshot
                )

                let total = Double(WorkbenchStage.workbenchRunStages.count)
                for command in plan {
                    if Task.isCancelled {
                        throw WorkbenchError.cancelled(makeCancellationReceipt(
                            stage: command.stage,
                            processCancellation: nil,
                            workspace: workspace,
                            outputWasTruncated: outputWasTruncated
                        ))
                    }
                    currentStage = command.stage
                    runStatusMessage = "Running \(command.stage.title)…"
                    appendLog("→ \(command.stage.rawValue): veriformis \(command.arguments.joined(separator: " "))")
                    let result = try await cli.run(
                        arguments: command.arguments,
                        controller: processController
                    ) { [weak self] line in
                        Task { @MainActor in
                            self?.appendLog(line)
                        }
                    }
                    combinedLog += result.combinedOutput
                    outputWasTruncated = outputWasTruncated || result.outputTruncated
                    if let logFileURL {
                        appendToLogFile(logFileURL, text: result.combinedOutput)
                    }
                    if let cancellation = result.cancellation {
                        throw WorkbenchError.cancelled(makeCancellationReceipt(
                            stage: command.stage,
                            processCancellation: cancellation,
                            workspace: workspace,
                            outputWasTruncated: outputWasTruncated
                        ))
                    }
                    if result.exitCode != 0 {
                        throw WorkbenchError.processFailed(
                            stage: command.stage.rawValue,
                            exitCode: result.exitCode,
                            message: result.combinedOutput.trimmingCharacters(in: .whitespacesAndNewlines)
                        )
                    }
                    completedStages.insert(command.stage)
                    progressPercent = min(100, (Double(completedStages.count) / total) * 100)
                }

                let manifest = Self.extractManifestSHA256(from: combinedLog)
                guard let manifest else {
                    throw WorkbenchError.processFailed(
                        stage: WorkbenchStage.seal.rawValue,
                        exitCode: 1,
                        message: "Seal completed without reporting the manifest SHA-256 required for transport."
                    )
                }
                currentStage = .package
                runStatusMessage = "Creating verified transport archive…"
                let packageArguments = [
                    "package",
                    bundle.path,
                    "-o",
                    transportArchive.path,
                    "--manifest-sha256",
                    manifest,
                ]
                appendLog("→ package: veriformis \(packageArguments.joined(separator: " "))")
                let packageResult = try await cli.run(
                    arguments: packageArguments,
                    controller: processController
                ) { [weak self] line in
                    Task { @MainActor in self?.appendLog(line) }
                }
                combinedLog += packageResult.combinedOutput
                outputWasTruncated = outputWasTruncated || packageResult.outputTruncated
                if let logFileURL {
                    appendToLogFile(logFileURL, text: packageResult.combinedOutput)
                }
                if let cancellation = packageResult.cancellation {
                    throw WorkbenchError.cancelled(makeCancellationReceipt(
                        stage: .package,
                        processCancellation: cancellation,
                        workspace: workspace,
                        outputWasTruncated: outputWasTruncated
                    ))
                }
                if packageResult.exitCode != 0 {
                    throw WorkbenchError.processFailed(
                        stage: WorkbenchStage.package.rawValue,
                        exitCode: packageResult.exitCode,
                        message: packageResult.combinedOutput.trimmingCharacters(in: .whitespacesAndNewlines)
                    )
                }
                completedStages.insert(.package)
                progressPercent = 100

                let archiveSHA256 = Self.extractArchiveSHA256(from: packageResult.combinedOutput)
                let assignment = Self.extractAssignmentDigest(from: combinedLog)
                let handoff = handoffSnapshot
                    ? URL(fileURLWithPath: bundle.path + ".aptus-handoff.json")
                    : nil
                if let handoff, FileManager.default.fileExists(atPath: handoff.path) {
                    appendLog("aptus handoff: \(handoff.path)")
                }

                currentStage = nil
                progressPercent = 100
                runStatusMessage = "Compile complete"
                lastResult = CompileResult(
                    workspaceURL: workspace,
                    bundleURL: bundle,
                    transportArchiveURL: transportArchive,
                    handoffURL: handoff.flatMap {
                        FileManager.default.fileExists(atPath: $0.path) ? $0 : nil
                    },
                    manifestSHA256: manifest,
                    transportArchiveSHA256: archiveSHA256,
                    assignmentDigest: assignment,
                    log: combinedLog,
                    logFileURL: logFileURL
                )
                appendLog("Compile complete.")
                if let logFileURL {
                    appendToLogFile(logFileURL, text: "Compile complete.\n")
                }
                refreshGoalPreview(workspace: workspace)

                recordHistory(
                    startedAt: startedAt,
                    status: .succeeded,
                    sources: sourcesSnapshot,
                    sourceRoot: sourceRootSnapshot,
                    objective: objectiveSnapshot,
                    allowEmptyEvaluation: allowEmptySnapshot,
                    writeAptusHandoff: handoffSnapshot,
                    splitRatioPPM: splitSnapshot,
                    workspace: workspace,
                    bundle: bundle,
                    handoff: lastResult?.handoffURL,
                    logFile: logFileURL,
                    manifest: manifest,
                    assignmentDigest: assignment,
                    error: nil,
                    failedStage: nil,
                    exitCode: nil,
                    cancellationReceipt: nil,
                    transportArchive: transportArchive,
                    transportArchiveSHA256: archiveSHA256
                )
            } catch WorkbenchError.cancelled(let receipt) {
                currentStage = nil
                runStatusMessage = "Compile cancelled"
                lastCancellation = receipt
                lastError = nil
                lastFailure = nil
                logExpanded = true
                let message = WorkbenchError.cancelled(receipt).localizedDescription
                appendLog(message)
                if let logFileURL {
                    appendToLogFile(logFileURL, text: "\(message)\n")
                }
                recordHistory(
                    startedAt: startedAt,
                    status: .cancelled,
                    sources: sourcesSnapshot,
                    sourceRoot: sourceRootSnapshot,
                    objective: objectiveSnapshot,
                    allowEmptyEvaluation: allowEmptySnapshot,
                    writeAptusHandoff: handoffSnapshot,
                    splitRatioPPM: splitSnapshot,
                    workspace: workspace,
                    bundle: bundle,
                    handoff: nil,
                    logFile: logFileURL,
                    manifest: nil,
                    assignmentDigest: nil,
                    error: message,
                    failedStage: receipt.stage,
                    exitCode: receipt.terminationStatus.map(Int.init),
                    cancellationReceipt: receipt,
                    transportArchive: nil,
                    transportArchiveSHA256: nil
                )
            } catch {
                let failure = Self.makeFailure(
                    error: error,
                    logLines: logLines,
                    workspace: workspace,
                    logFile: logFileURL
                )
                currentStage = nil
                runStatusMessage = failure.summary
                lastFailure = failure
                lastError = failure.summary + "\n" + failure.message
                logExpanded = true
                appendLog("error: \(failure.summary)")
                if let logFileURL {
                    appendToLogFile(
                        logFileURL,
                        text: "error: \(failure.summary)\n\(failure.message)\n"
                    )
                }
                recordHistory(
                    startedAt: startedAt,
                    status: .failed,
                    sources: sourcesSnapshot,
                    sourceRoot: sourceRootSnapshot,
                    objective: objectiveSnapshot,
                    allowEmptyEvaluation: allowEmptySnapshot,
                    writeAptusHandoff: handoffSnapshot,
                    splitRatioPPM: splitSnapshot,
                    workspace: workspace,
                    bundle: bundle,
                    handoff: nil,
                    logFile: logFileURL,
                    manifest: nil,
                    assignmentDigest: nil,
                    error: failure.summary,
                    failedStage: failure.stage,
                    exitCode: failure.exitCode.map { Int($0) },
                    cancellationReceipt: nil,
                    transportArchive: nil,
                    transportArchiveSHA256: nil
                )
            }
        }
    }

    /// Cancel the active stage, retaining its workspace and recording how the
    /// child process exited. Completion runs after TERM/KILL recovery is done.
    func cancelCompile(onFinished: (() -> Void)? = nil) {
        if let onFinished {
            guard isRunning else {
                onFinished()
                return
            }
            runFinishedCallbacks.append(onFinished)
        }
        guard isRunning else { return }
        if cancellationRequestedAt == nil {
            cancellationRequestedAt = Date()
            runStatusMessage = "Cancelling…"
            appendLog("Cancellation requested; preserving the current workspace…")
        }
        compileTask?.cancel()
        activeProcessController?.cancel()
    }

    /// Restore compile form from a history entry and start again.
    func reRun(from entry: RunHistoryEntry) {
        guard !isRunning else { return }
        sourceURLs = entry.sourcePaths.map { URL(fileURLWithPath: $0) }
        if let root = entry.sourceRootPath {
            sourceRootURL = URL(fileURLWithPath: root)
            userPinnedSourceRoot = true
        } else {
            userPinnedSourceRoot = false
            sourceRootURL = Self.defaultSourceRoot(for: sourceURLs)
        }
        if let objective = TrainingObjective(rawValue: entry.objective) {
            self.objective = objective
        }
        // Legacy entries without recorded values fall back to the current
        // fail-closed defaults; explicitly recorded opt-ins are preserved.
        allowEmptyEvaluation = entry.allowEmptyEvaluation ?? Self.defaultAllowEmptyEvaluation
        writeAptusHandoff = entry.requestsAptusHandoff
        splitRatioPPM = entry.splitRatioPPM ?? Self.defaultSplitRatioPPM
        let parent = URL(fileURLWithPath: entry.workspacePath).deletingLastPathComponent()
        if FileManager.default.fileExists(atPath: parent.path) {
            outputDirectoryURL = parent
        }
        destination = .compile
        compile()
    }

    func reRunLastConfiguration() {
        if let entry = runHistory.first {
            reRun(from: entry)
        } else {
            compile()
        }
    }

    func copyToPasteboard(_ text: String, label: String) {
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(text, forType: .string)
        lastCopiedNotice = "Copied \(label)"
        runStatusMessage = "Copied \(label)"
        appendLog("copied \(label)")
    }

    func copyManifestIfAvailable() {
        if let sha = lastResult?.manifestSHA256 ?? selectedHistoryEntry?.manifestSHA256 {
            copyToPasteboard(sha, label: "manifest SHA-256")
        }
    }

    func copyAssignmentDigestIfAvailable() {
        if let digest = lastResult?.assignmentDigest ?? selectedHistoryEntry?.assignmentDigest {
            copyToPasteboard(digest, label: "assignment digest")
        }
    }

    func appendLog(_ line: String) {
        let trimmed = line.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        logLines.append(trimmed)
        if logLines.count > 2_000 {
            logLines.removeFirst(logLines.count - 2_000)
        }
    }

    func reveal(_ url: URL) {
        NSWorkspace.shared.activateFileViewerSelecting([url])
    }

    func openLogFile(_ url: URL) {
        NSWorkspace.shared.open(url)
    }

    nonisolated static func extractManifestSHA256(from log: String) -> String? {
        extractLabeledDigest(from: log, label: "manifest sha-256")
    }

    nonisolated static func extractAssignmentDigest(from log: String) -> String? {
        extractLabeledDigest(from: log, label: "assignment digest")
    }

    nonisolated static func extractArchiveSHA256(from log: String) -> String? {
        extractLabeledDigest(from: log, label: "archive sha-256")
    }

    nonisolated static func extractLabeledDigest(from log: String, label: String) -> String? {
        let needle = label.lowercased() + ":"
        for line in log.split(separator: "\n") {
            let text = String(line)
            let lower = text.lowercased()
            guard let range = lower.range(of: needle) else { continue }
            let value = text[range.upperBound...].trimmingCharacters(in: .whitespaces)
            if !value.isEmpty { return value }
        }
        return nil
    }

    nonisolated static func makeFailure(
        error: Error,
        logLines: [String],
        workspace: URL,
        logFile: URL?
    ) -> CompileFailure {
        let lastLines = Array(logLines.suffix(12))
        if let workbenchError = error as? WorkbenchError {
            switch workbenchError {
            case .processFailed(let stage, let exitCode, let message):
                return CompileFailure(
                    stage: stage,
                    exitCode: exitCode,
                    message: message,
                    lastLogLines: lastLines,
                    workspaceURL: FileManager.default.fileExists(atPath: workspace.path) ? workspace : nil,
                    logFileURL: logFile
                )
            default:
                break
            }
        }
        return CompileFailure(
            stage: "unknown",
            exitCode: nil,
            message: error.localizedDescription,
            lastLogLines: lastLines,
            workspaceURL: FileManager.default.fileExists(atPath: workspace.path) ? workspace : nil,
            logFileURL: logFile
        )
    }

    private func makeCancellationReceipt(
        stage: WorkbenchStage?,
        processCancellation: CLIProcessCancellation?,
        workspace: URL,
        outputWasTruncated: Bool
    ) -> RunCancellationReceipt {
        RunCancellationReceipt(
            requestedAt: cancellationRequestedAt ?? Date(),
            stage: stage?.rawValue,
            processIdentifier: processCancellation?.processIdentifier,
            terminationStatus: processCancellation?.terminationStatus,
            terminationEscalated: processCancellation?.terminationEscalated ?? false,
            completedStages: WorkbenchStage.workbenchRunStages
                .filter { completedStages.contains($0) }
                .map(\.rawValue),
            workspaceRetained: FileManager.default.fileExists(atPath: workspace.path),
            outputWasTruncated: outputWasTruncated
        )
    }

    /// Directory that contains every source. Never a file path.
    nonisolated static func defaultSourceRoot(for sources: [URL]) -> URL? {
        guard !sources.isEmpty else { return nil }
        let directories: [URL] = sources.map { url in
            let standardized = url.standardizedFileURL
            var isDir: ObjCBool = false
            if FileManager.default.fileExists(atPath: standardized.path, isDirectory: &isDir),
               isDir.boolValue
            {
                return standardized
            }
            return standardized.deletingLastPathComponent()
        }
        guard var shared = directories.first?.pathComponents, !shared.isEmpty else { return nil }
        for directory in directories.dropFirst() {
            let other = directory.pathComponents
            var index = 0
            while index < shared.count, index < other.count, shared[index] == other[index] {
                index += 1
            }
            shared = Array(shared.prefix(index))
        }
        guard !shared.isEmpty else { return nil }
        if shared.first == "/" {
            return shared.dropFirst().reduce(URL(fileURLWithPath: "/")) { partial, component in
                partial.appendingPathComponent(component)
            }
        }
        return shared.dropFirst().reduce(URL(fileURLWithPath: shared[0])) { partial, component in
            partial.appendingPathComponent(component)
        }
    }

    private func loadSettings() {
        cliOverridePath = defaults.string(forKey: cliOverrideKey) ?? ""
        defaultOutputPath = defaults.string(forKey: defaultOutputKey) ?? ""
        if !cliOverridePath.isEmpty {
            setenv("VERIFORMIS_CLI", cliOverridePath, 1)
        }
    }

    private func applyDefaultOutputIfNeeded() {
        if outputDirectoryURL != nil { return }
        if !defaultOutputPath.isEmpty {
            let url = URL(fileURLWithPath: defaultOutputPath)
            try? FileManager.default.createDirectory(at: url, withIntermediateDirectories: true)
            outputDirectoryURL = url
            return
        }
        let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first
            ?? URL(fileURLWithPath: NSHomeDirectory()).appendingPathComponent("Documents")
        let fallback = docs.appendingPathComponent("Veriformis", isDirectory: true)
        try? FileManager.default.createDirectory(at: fallback, withIntermediateDirectories: true)
        outputDirectoryURL = fallback
        defaultOutputPath = fallback.path
        defaults.set(fallback.path, forKey: defaultOutputKey)
    }

    private func supportDirectory() -> URL {
        if let supportDirectoryOverride {
            try? FileManager.default.createDirectory(
                at: supportDirectoryOverride,
                withIntermediateDirectories: true
            )
            return supportDirectoryOverride
        }
        let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first
            ?? URL(fileURLWithPath: NSTemporaryDirectory())
        let dir = base.appendingPathComponent("com.veriformis.workbench", isDirectory: true)
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        return dir
    }

    private func historyFileURL() -> URL {
        supportDirectory().appendingPathComponent("run-history.json")
    }

    private func loadHistory() {
        let url = historyFileURL()
        guard let data = try? Data(contentsOf: url),
              let decoded = try? JSONDecoder().decode([RunHistoryEntry].self, from: data)
        else {
            runHistory = []
            return
        }
        runHistory = decoded
        selectedHistoryID = decoded.first?.id
    }

    private func saveHistory() {
        let url = historyFileURL()
        if let data = try? JSONEncoder().encode(runHistory) {
            try? data.write(to: url, options: .atomic)
        }
    }

    private func recordHistory(
        startedAt: Date,
        status: RunStatus,
        sources: [URL],
        sourceRoot: URL,
        objective: TrainingObjective,
        allowEmptyEvaluation: Bool,
        writeAptusHandoff: Bool,
        splitRatioPPM: Int,
        workspace: URL,
        bundle: URL,
        handoff: URL?,
        logFile: URL?,
        manifest: String?,
        assignmentDigest: String?,
        error: String?,
        failedStage: String?,
        exitCode: Int?,
        cancellationReceipt: RunCancellationReceipt?,
        transportArchive: URL?,
        transportArchiveSHA256: String?
    ) {
        let entry = RunHistoryEntry(
            id: UUID(),
            startedAt: startedAt,
            finishedAt: Date(),
            status: status,
            objective: objective.rawValue,
            primarySourceName: sources.first?.lastPathComponent ?? "(none)",
            sourcePaths: sources.map(\.path),
            workspacePath: workspace.path,
            bundlePath: bundle.path,
            handoffPath: handoff?.path,
            logFilePath: logFile?.path,
            manifestSHA256: manifest,
            assignmentDigest: assignmentDigest,
            errorSummary: error,
            sourceRootPath: sourceRoot.path,
            allowEmptyEvaluation: allowEmptyEvaluation,
            writeAptusHandoff: writeAptusHandoff,
            splitRatioPPM: splitRatioPPM,
            failedStage: failedStage,
            exitCode: exitCode,
            cancellationReceipt: cancellationReceipt,
            transportArchivePath: transportArchive?.path,
            transportArchiveSHA256: transportArchiveSHA256
        )
        runHistory.insert(entry, at: 0)
        if runHistory.count > historyLimit {
            runHistory = Array(runHistory.prefix(historyLimit))
        }
        selectedHistoryID = entry.id
        saveHistory()
    }

    private func appendToLogFile(_ url: URL, text: String) {
        guard let data = text.data(using: .utf8) else { return }
        if FileManager.default.fileExists(atPath: url.path) {
            if let handle = try? FileHandle(forWritingTo: url) {
                defer { try? handle.close() }
                _ = try? handle.seekToEnd()
                try? handle.write(contentsOf: data)
            }
        } else {
            try? data.write(to: url)
        }
    }
}
