import AppKit
import Foundation
import SwiftUI
import UniformTypeIdentifiers

@MainActor
final class WorkbenchViewModel: ObservableObject {
    nonisolated static let defaultWriteAptusHandoff = false

    // Navigation
    @Published var destination: SidebarDestination = .compile

    // Compile form
    @Published var sourceURLs: [URL] = [] {
        didSet {
            if oldValue != sourceURLs { invalidateCompilePreflight() }
        }
    }
    @Published var sourceRootURL: URL? {
        didSet {
            if oldValue != sourceRootURL { invalidateCompilePreflight() }
        }
    }
    private var userPinnedSourceRoot = false
    @Published var outputDirectoryURL: URL?
    /// Plain-language goal and preset selection (Phase 6.4). Recipe defaults
    /// are never Swift constants: they come from `veriformis presets`.
    @Published var selectedGoalID: String? {
        didSet {
            if oldValue != selectedGoalID { invalidateCompilePreflight() }
        }
    }
    @Published var selectedPresetID: String? {
        didSet {
            if oldValue != selectedPresetID { invalidateCompilePreflight() }
        }
    }
    /// `--allow-empty-evaluation` is an explicit per-run opt-in, never a
    /// silent default; the CLI preset data requires evaluation otherwise.
    @Published var allowEmptyEvaluation = false {
        didSet {
            if oldValue != allowEmptyEvaluation { invalidateCompilePreflight() }
        }
    }
    /// Operator override for `--split-ratio-ppm`; nil means the preset value.
    @Published var splitRatioPPM: Int? {
        didSet {
            if oldValue != splitRatioPPM { invalidateCompilePreflight() }
        }
    }
    @Published var writeAptusHandoff = defaultWriteAptusHandoff {
        didSet {
            if oldValue != writeAptusHandoff { invalidateCompilePreflight() }
        }
    }
    @Published private(set) var taxonomyHelpState: TaxonomyHelpState = .idle
    @Published private(set) var goalCatalogState: GoalCatalogState = .idle
    @Published private(set) var recipePresetState: RecipePresetState = .idle
    @Published private(set) var goalPreviewState: GoalPreviewState = .idle
    @Published private(set) var compilePreflightState: CompilePreflightState = .idle

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

    private var cli: VeriformisCLI? {
        didSet { invalidateCompilePreflight() }
    }
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
    private var goalCatalogTask: Task<Void, Never>?
    private var goalCatalogController: CLIProcessController?
    private var recipePresetTask: Task<Void, Never>?
    private var recipePresetController: CLIProcessController?
    /// A legacy history entry's objective awaiting a loaded goal catalog.
    private var pendingLegacyObjective: String?
    private var goalPreviewTask: Task<Void, Never>?
    private var goalPreviewController: CLIProcessController?
    private var compilePreflightTask: Task<Void, Never>?
    private var compilePreflightController: CLIProcessController?
    private var compilePreflightRequestSnapshot: CompilePreflightRequest?

    var canCompile: Bool {
        guard !isRunning,
              cli != nil,
              !sourceURLs.isEmpty,
              resolvedSourceRoot != nil,
              outputDirectoryURL != nil,
              let request = currentCompilePreflightRequest(),
              compilePreflightRequestSnapshot == request,
              case .ready(let report) = compilePreflightState
        else { return false }
        return report.admitted
    }

    var canPreflight: Bool {
        !isRunning && currentCompilePreflightRequest() != nil
    }

    var compileBlockedReason: String? {
        if isRunning { return "A compile is already running." }
        if cli == nil { return "CLI is not ready. Open Settings or relaunch via ./script/build_and_run.sh." }
        if sourceURLs.isEmpty { return "Add at least one source file." }
        if resolvedSourceRoot == nil { return "Source root directory is missing." }
        if outputDirectoryURL == nil { return "Choose an output folder (or set a default in Settings)." }
        if selectedGoalID == nil || selectedPresetID == nil {
            return "Goal catalog and recipe presets are not loaded yet."
        }
        switch compilePreflightState {
        case .idle:
            return "Check the current sources and recipe before compiling."
        case .loading:
            return "Compile preflight is still running."
        case .unavailable:
            return "Compile preflight is unavailable; retry it before compiling."
        case .ready(let report) where !report.admitted:
            return "Compile preflight found blockers. Resolve them and check again."
        case .ready:
            if compilePreflightRequestSnapshot != currentCompilePreflightRequest() {
                return "The compile configuration changed; run preflight again."
            }
        }
        return nil
    }

    /// The selected goal's catalog entry, when the catalog is loaded.
    var selectedGoal: GoalCatalogGoal? {
        guard case .ready(let catalog) = goalCatalogState, let selectedGoalID else { return nil }
        return catalog.goal(withID: selectedGoalID)
    }

    /// The selected preset entry, when the presets are loaded.
    var selectedPreset: RecipePresetEntry? {
        guard case .ready(let catalog) = recipePresetState, let selectedPresetID else { return nil }
        return catalog.preset(withID: selectedPresetID)
    }

    /// Choose a goal and move the preset to that goal's safe preset.
    func selectGoal(_ goalID: String) {
        selectedGoalID = goalID
        if case .ready(let catalog) = recipePresetState {
            selectedPresetID = catalog.safePreset(forGoal: goalID)?.presetID
        }
    }

    private func adoptLoadedSelection() {
        guard case .ready(let goals) = goalCatalogState,
              case .ready(let presets) = recipePresetState
        else { return }
        if let pending = pendingLegacyObjective,
           let goal = goals.goals.first(where: { $0.objective.rawValue == pending })
        {
            pendingLegacyObjective = nil
            selectedGoalID = goal.goalID
            selectedPresetID = nil
        }
        if selectedGoalID == nil || goals.goal(withID: selectedGoalID ?? "") == nil {
            selectedGoalID = goals.goals.first?.goalID
        }
        if let goalID = selectedGoalID,
           selectedPresetID == nil || presets.preset(withID: selectedPresetID ?? "")?.goalID != goalID
        {
            selectedPresetID = presets.safePreset(forGoal: goalID)?.presetID
        }
    }

    func refreshGoalCatalog() {
        invalidateCompilePreflight()
        goalCatalogTask?.cancel()
        goalCatalogController?.cancel()
        goalCatalogTask = nil
        goalCatalogController = nil
        guard let cli else {
            goalCatalogState = .unavailable("Veriformis CLI is unavailable.")
            return
        }
        let controller = CLIProcessController()
        goalCatalogController = controller
        goalCatalogState = .loading
        goalCatalogTask = Task { [weak self] in
            let nextState: GoalCatalogState
            do {
                let catalog = try await cli.discoverGoals(controller: controller)
                try Task.checkCancellation()
                nextState = .ready(catalog)
            } catch is CancellationError {
                nextState = .unavailable("Goal discovery was cancelled.")
            } catch {
                nextState = .unavailable(error.localizedDescription)
            }
            guard let self, self.goalCatalogController === controller else { return }
            self.goalCatalogState = nextState
            self.goalCatalogController = nil
            self.goalCatalogTask = nil
            self.adoptLoadedSelection()
        }
    }

    func refreshRecipePresets() {
        invalidateCompilePreflight()
        recipePresetTask?.cancel()
        recipePresetController?.cancel()
        recipePresetTask = nil
        recipePresetController = nil
        guard let cli else {
            recipePresetState = .unavailable("Veriformis CLI is unavailable.")
            return
        }
        let controller = CLIProcessController()
        recipePresetController = controller
        recipePresetState = .loading
        recipePresetTask = Task { [weak self] in
            let nextState: RecipePresetState
            do {
                let catalog = try await cli.discoverPresets(controller: controller)
                try Task.checkCancellation()
                nextState = .ready(catalog)
            } catch is CancellationError {
                nextState = .unavailable("Recipe preset discovery was cancelled.")
            } catch {
                nextState = .unavailable(error.localizedDescription)
            }
            guard let self, self.recipePresetController === controller else { return }
            self.recipePresetState = nextState
            self.recipePresetController = nil
            self.recipePresetTask = nil
            self.adoptLoadedSelection()
        }
    }

    /// Apply already-decoded catalogs (tests and deterministic startup paths),
    /// cancelling any in-flight discovery so a late result cannot replace them.
    func applyCatalogs(goals: GoalCatalog, presets: RecipePresetCatalog) {
        invalidateCompilePreflight()
        goalCatalogTask?.cancel()
        goalCatalogController?.cancel()
        goalCatalogTask = nil
        goalCatalogController = nil
        recipePresetTask?.cancel()
        recipePresetController?.cancel()
        recipePresetTask = nil
        recipePresetController = nil
        goalCatalogState = .ready(goals)
        recipePresetState = .ready(presets)
        adoptLoadedSelection()
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
            refreshGoalCatalog()
            refreshRecipePresets()
        } catch {
            cli = nil
            refreshTaxonomyHelp()
            refreshGoalCatalog()
            refreshRecipePresets()
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

    /// Cancel a raw-source preflight and discard its report. A report is valid
    /// only for the exact immutable form snapshot that produced it.
    func cancelCompilePreflight() {
        compilePreflightTask?.cancel()
        compilePreflightController?.cancel()
        compilePreflightTask = nil
        compilePreflightController = nil
        compilePreflightRequestSnapshot = nil
        compilePreflightState = .idle
    }

    /// Check the current source and recipe selection without creating a workspace.
    func refreshCompilePreflight() {
        cancelCompilePreflight()
        guard !isRunning else { return }
        guard let cli else {
            compilePreflightState = .unavailable("Veriformis CLI is unavailable.")
            return
        }
        guard let request = currentCompilePreflightRequest() else {
            compilePreflightState = .idle
            return
        }

        let controller = CLIProcessController()
        compilePreflightController = controller
        compilePreflightState = .loading
        compilePreflightTask = Task { [weak self] in
            let nextState: CompilePreflightState
            do {
                let report = try await cli.preflight(request, controller: controller)
                try Task.checkCancellation()
                nextState = .ready(report)
            } catch is CancellationError {
                nextState = .idle
            } catch {
                nextState = .unavailable(error.localizedDescription)
            }
            guard let self,
                  self.compilePreflightController === controller,
                  self.currentCompilePreflightRequest() == request
            else { return }
            self.compilePreflightState = nextState
            if case .ready = nextState {
                self.compilePreflightRequestSnapshot = request
            } else {
                self.compilePreflightRequestSnapshot = nil
            }
            self.compilePreflightController = nil
            self.compilePreflightTask = nil
        }
    }

    private func invalidateCompilePreflight() {
        compilePreflightTask?.cancel()
        compilePreflightController?.cancel()
        compilePreflightTask = nil
        compilePreflightController = nil
        compilePreflightRequestSnapshot = nil
        compilePreflightState = .idle
    }

    private func currentCompilePreflightRequest() -> CompilePreflightRequest? {
        guard !sourceURLs.isEmpty,
              let sourceRoot = resolvedSourceRoot,
              let goal = selectedGoalID,
              let presetID = selectedPresetID,
              let preset = selectedPreset,
              preset.presetID == presetID,
              preset.goalID == goal
        else { return nil }
        return CompilePreflightRequest(
            sources: sourceURLs,
            sourceRoot: sourceRoot,
            goal: goal,
            preset: presetID,
            representation: preset.representationID,
            splitRatioPPM: splitRatioPPM,
            consumerProfile: writeAptusHandoff ? "aptus-handoff-v1" : nil,
            evaluationRequired: allowEmptyEvaluation ? false : nil
        )
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
        runStatusMessage = "Checking sources and recipe…"

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

        guard let goalSnapshot = selectedGoalID, let presetSnapshot = selectedPresetID else {
            lastError = "Goal catalog and recipe presets are not loaded yet."
            return
        }
        guard let preflightRequest = currentCompilePreflightRequest() else {
            lastError = "The selected goal, preset, and representation are not ready for preflight."
            return
        }
        cancelCompilePreflight()
        compilePreflightState = .loading
        isRunning = true
        showRunSheet = false
        let startedAt = Date()
        let sourcesSnapshot = sourceURLs
        let sourceRootSnapshot = sourceRoot
        let objectiveSnapshot = selectedGoal?.objective ?? .fullText
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
            let cli: VeriformisCLI
            do {
                cli = try self.cli ?? VeriformisCLI.resolve()
                if self.cli == nil {
                    self.cli = cli
                    self.compilePreflightState = .loading
                }
                let report = try await cli.preflight(
                    preflightRequest,
                    controller: processController
                )
                try Task.checkCancellation()
                guard currentCompilePreflightRequest() == preflightRequest else {
                    compilePreflightRequestSnapshot = nil
                    compilePreflightState = .idle
                    runStatusMessage = "Configuration changed; check it again"
                    return
                }
                compilePreflightRequestSnapshot = preflightRequest
                compilePreflightState = .ready(report)
                guard report.admitted else {
                    runStatusMessage = "Preflight found blockers"
                    return
                }
            } catch is CancellationError {
                if currentCompilePreflightRequest() == preflightRequest {
                    compilePreflightRequestSnapshot = nil
                    compilePreflightState = .idle
                }
                runStatusMessage = "Preflight cancelled"
                return
            } catch {
                if currentCompilePreflightRequest() == preflightRequest {
                    compilePreflightRequestSnapshot = nil
                    compilePreflightState = .unavailable(error.localizedDescription)
                }
                runStatusMessage = "Preflight unavailable"
                lastError = error.localizedDescription
                return
            }

            showRunSheet = true
            runStatusMessage = "Starting compile…"
            appendLog("Preflight admitted the current captured source snapshot.")
            do {

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
                    goal: goalSnapshot,
                    preset: presetSnapshot,
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
                    goalID: goalSnapshot,
                    presetID: presetSnapshot,
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
                    goalID: goalSnapshot,
                    presetID: presetSnapshot,
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
                    goalID: goalSnapshot,
                    presetID: presetSnapshot,
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
            if showRunSheet {
                appendLog("Cancellation requested; preserving the current workspace…")
            } else {
                appendLog("Cancellation requested before workspace creation…")
            }
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
        if let goalID = entry.goalID {
            selectGoal(goalID)
            if let presetID = entry.presetID {
                selectedPresetID = presetID
            }
        } else if case .ready(let catalog) = goalCatalogState,
                  let goal = catalog.goals.first(where: { $0.objective.rawValue == entry.objective })
        {
            // Legacy entries recorded only the objective; map it to its goal.
            selectGoal(goal.goalID)
        } else {
            // Catalog not loaded yet: apply the legacy objective once it is.
            pendingLegacyObjective = entry.objective
        }
        // Legacy entries without recorded values fall back to the fail-closed
        // opt-in state and the preset value; explicit overrides are preserved.
        allowEmptyEvaluation = entry.allowEmptyEvaluation ?? false
        writeAptusHandoff = entry.requestsAptusHandoff
        splitRatioPPM = entry.splitRatioPPM
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
        splitRatioPPM: Int?,
        goalID: String? = nil,
        presetID: String? = nil,
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
            goalID: goalID,
            presetID: presetID,
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
