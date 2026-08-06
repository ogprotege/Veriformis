import AppKit
import Foundation
import SwiftUI
import UniformTypeIdentifiers

@MainActor
final class WorkbenchViewModel: ObservableObject {
    // Navigation
    @Published var destination: SidebarDestination = .compile

    // Compile form
    @Published var sourceURLs: [URL] = []
    @Published var sourceRootURL: URL?
    private var userPinnedSourceRoot = false
    @Published var outputDirectoryURL: URL?
    @Published var objective: TrainingObjective = .fullText
    @Published var allowEmptyEvaluation = true
    @Published var splitRatioPPM = 400_000
    @Published var writeAptusHandoff = true

    // Run state
    @Published var isRunning = false
    @Published var showRunSheet = false
    @Published var currentStage: WorkbenchStage?
    @Published var completedStages: Set<WorkbenchStage> = []
    @Published var progressPercent: Double = 0
    @Published var logLines: [String] = []
    @Published var logExpanded = true
    @Published var lastError: String?
    @Published var lastResult: CompileResult?
    @Published var runStatusMessage = "Ready"

    // History + settings
    @Published var runHistory: [RunHistoryEntry] = []
    @Published var selectedHistoryID: UUID?
    @Published var cliOverridePath: String = ""
    @Published var resolvedCLIDescription: String = "(not resolved)"
    @Published var defaultOutputPath: String = ""

    private var cli: VeriformisCLI?
    private let defaults = UserDefaults.standard
    private let historyKey = "veriformis.workbench.runHistory.v1"
    private let defaultOutputKey = "veriformis.workbench.defaultOutput"
    private let cliOverrideKey = "veriformis.workbench.cliOverride"
    private let historyLimit = 100

    var canCompile: Bool {
        !isRunning
            && cli != nil
            && !sourceURLs.isEmpty
            && resolvedSourceRoot != nil
            && outputDirectoryURL != nil
    }

    var compileBlockedReason: String? {
        if isRunning { return "A compile is already running." }
        if cli == nil { return "CLI is not ready. Open Settings or relaunch via run_workbench.sh." }
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

    init() {
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
        } catch {
            cli = nil
            resolvedCLIDescription = "(missing)"
            lastError = error.localizedDescription
            appendLog("error: \(error.localizedDescription)")
            appendLog("hint: use macos/scripts/run_workbench.sh from the repo so the Debug app is rebuilt and opened.")
            runStatusMessage = "CLI missing"
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
        lastResult = nil
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
        let objectiveSnapshot = objective

        Task {
            defer { isRunning = false }
            var combinedLog = ""
            var workspace = outputDirectory
            var bundle = outputDirectory
            var logFileURL: URL?
            do {
                let cli = try self.cli ?? VeriformisCLI.resolve()
                self.cli = cli

                let stamp = ISO8601DateFormatter().string(from: Date()).replacingOccurrences(of: ":", with: "-")
                workspace = outputDirectory.appendingPathComponent("workspace-\(stamp)", isDirectory: true)
                bundle = outputDirectory.appendingPathComponent("dataset-\(stamp).vfbundle", isDirectory: true)
                try FileManager.default.createDirectory(at: workspace, withIntermediateDirectories: true)
                logFileURL = workspace.appendingPathComponent("run.log")

                let plan = VeriformisCLI.compilePlan(
                    sources: sourcesSnapshot,
                    sourceRoot: sourceRoot,
                    workspace: workspace,
                    bundle: bundle,
                    objective: objectiveSnapshot,
                    allowEmptyEvaluation: allowEmptyEvaluation,
                    splitRatioPPM: splitRatioPPM,
                    includeHandoff: writeAptusHandoff
                )

                let total = Double(WorkbenchStage.pipelineStages.count)
                for command in plan {
                    currentStage = command.stage
                    runStatusMessage = "Running \(command.stage.title)…"
                    appendLog("→ \(command.stage.rawValue): veriformis \(command.arguments.joined(separator: " "))")
                    let result = try cli.run(arguments: command.arguments) { [weak self] line in
                        Task { @MainActor in
                            self?.appendLog(line)
                        }
                    }
                    combinedLog += result.combinedOutput
                    if let logFileURL {
                        appendToLogFile(logFileURL, text: result.combinedOutput)
                    }
                    if result.exitCode != 0 {
                        throw WorkbenchError.processFailed(
                            stage: command.stage.rawValue,
                            message: result.combinedOutput.trimmingCharacters(in: .whitespacesAndNewlines)
                        )
                    }
                    completedStages.insert(command.stage)
                    progressPercent = min(100, (Double(completedStages.count) / total) * 100)
                }

                let manifest = Self.extractManifestSHA256(from: combinedLog)
                let handoff = writeAptusHandoff
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
                    handoffURL: handoff.flatMap {
                        FileManager.default.fileExists(atPath: $0.path) ? $0 : nil
                    },
                    manifestSHA256: manifest,
                    log: combinedLog,
                    logFileURL: logFileURL
                )
                appendLog("Compile complete.")
                if let logFileURL {
                    appendToLogFile(logFileURL, text: "Compile complete.\n")
                }

                recordHistory(
                    startedAt: startedAt,
                    status: .succeeded,
                    sources: sourcesSnapshot,
                    objective: objectiveSnapshot,
                    workspace: workspace,
                    bundle: bundle,
                    handoff: lastResult?.handoffURL,
                    logFile: logFileURL,
                    manifest: manifest,
                    error: nil
                )
            } catch {
                currentStage = nil
                runStatusMessage = "Compile failed"
                lastError = error.localizedDescription
                appendLog("error: \(error.localizedDescription)")
                if let logFileURL {
                    appendToLogFile(logFileURL, text: "error: \(error.localizedDescription)\n")
                }
                recordHistory(
                    startedAt: startedAt,
                    status: .failed,
                    sources: sourcesSnapshot,
                    objective: objectiveSnapshot,
                    workspace: workspace,
                    bundle: bundle,
                    handoff: nil,
                    logFile: logFileURL,
                    manifest: nil,
                    error: error.localizedDescription
                )
            }
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
        for line in log.split(separator: "\n") {
            let text = String(line)
            if text.lowercased().contains("manifest sha-256:") {
                let parts = text.split(separator: ":", maxSplits: 1)
                if parts.count == 2 {
                    return parts[1].trimmingCharacters(in: .whitespaces)
                }
            }
        }
        return nil
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
        objective: TrainingObjective,
        workspace: URL,
        bundle: URL,
        handoff: URL?,
        logFile: URL?,
        manifest: String?,
        error: String?
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
            errorSummary: error
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
