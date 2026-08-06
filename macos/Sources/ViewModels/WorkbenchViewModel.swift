import AppKit
import Foundation
import SwiftUI
import UniformTypeIdentifiers

@MainActor
final class WorkbenchViewModel: ObservableObject {
    @Published var sourceURLs: [URL] = []
    @Published var sourceRootURL: URL?
    /// True after the user picks Source root… so auto-inference does not overwrite it.
    private var userPinnedSourceRoot = false
    @Published var outputDirectoryURL: URL?
    @Published var objective: TrainingObjective = .fullText
    @Published var allowEmptyEvaluation = true
    @Published var splitRatioPPM = 400_000
    @Published var writeAptusHandoff = true

    @Published var isRunning = false
    @Published var currentStage: WorkbenchStage?
    @Published var completedStages: Set<WorkbenchStage> = []
    @Published var logLines: [String] = []
    @Published var lastError: String?
    @Published var lastResult: CompileResult?

    private var cli: VeriformisCLI?

    var canCompile: Bool {
        !isRunning && !sourceURLs.isEmpty && resolvedSourceRoot != nil && outputDirectoryURL != nil
    }

    var resolvedSourceRoot: URL? {
        sourceRootURL ?? sourceURLs.first?.deletingLastPathComponent()
    }

    func bootstrapCLI() {
        appendLog("Workbench bootstrap…")
        appendLog(VeriformisCLI.resolutionDiagnostics())
        do {
            cli = try VeriformisCLI.resolve()
            let prefix = cli!.prefixArguments.isEmpty
                ? ""
                : " " + cli!.prefixArguments.joined(separator: " ")
            appendLog("CLI ready: \(cli!.executableURL.path)\(prefix)")
        } catch {
            lastError = error.localizedDescription
            appendLog("error: \(error.localizedDescription)")
            appendLog("hint: use macos/scripts/run_workbench.sh from the repo so the Debug app is rebuilt and opened.")
        }
    }

    func addSources(_ urls: [URL]) {
        let existing = Set(sourceURLs.map(\.path))
        for url in urls where !existing.contains(url.path) {
            sourceURLs.append(url)
        }
        sourceURLs.sort { $0.path < $1.path }
        // Always recompute when the user has not pinned an explicit root.
        // (A single file must use its parent directory, never the file path.)
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

    func compile() {
        guard !isRunning else { return }
        lastError = nil
        lastResult = nil
        completedStages = []
        currentStage = nil

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

        isRunning = true
        Task {
            defer { isRunning = false }
            do {
                let cli = try self.cli ?? VeriformisCLI.resolve()
                self.cli = cli

                let stamp = ISO8601DateFormatter().string(from: Date()).replacingOccurrences(of: ":", with: "-")
                let workspace = outputDirectory.appendingPathComponent("workspace-\(stamp)", isDirectory: true)
                let bundle = outputDirectory.appendingPathComponent("dataset-\(stamp).vfbundle", isDirectory: true)

                let plan = VeriformisCLI.compilePlan(
                    sources: sourceURLs,
                    sourceRoot: sourceRoot,
                    workspace: workspace,
                    bundle: bundle,
                    objective: objective,
                    allowEmptyEvaluation: allowEmptyEvaluation,
                    splitRatioPPM: splitRatioPPM,
                    includeHandoff: writeAptusHandoff
                )

                var combinedLog = ""
                for command in plan {
                    currentStage = command.stage
                    appendLog("→ \(command.stage.rawValue): veriformis \(command.arguments.joined(separator: " "))")
                    let result = try cli.run(arguments: command.arguments) { [weak self] line in
                        Task { @MainActor in
                            self?.appendLog(line)
                        }
                    }
                    combinedLog += result.combinedOutput
                    if result.exitCode != 0 {
                        throw WorkbenchError.processFailed(
                            stage: command.stage.rawValue,
                            message: result.combinedOutput.trimmingCharacters(in: .whitespacesAndNewlines)
                        )
                    }
                    completedStages.insert(command.stage)
                }

                let manifest = Self.extractManifestSHA256(from: combinedLog)
                let handoff = writeAptusHandoff
                    ? URL(fileURLWithPath: bundle.path + ".aptus-handoff.json")
                    : nil
                if let handoff, FileManager.default.fileExists(atPath: handoff.path) {
                    appendLog("aptus handoff: \(handoff.path)")
                }

                currentStage = nil
                lastResult = CompileResult(
                    workspaceURL: workspace,
                    bundleURL: bundle,
                    handoffURL: handoff.flatMap {
                        FileManager.default.fileExists(atPath: $0.path) ? $0 : nil
                    },
                    manifestSHA256: manifest,
                    log: combinedLog
                )
                appendLog("Compile complete.")
            } catch {
                currentStage = nil
                lastError = error.localizedDescription
                appendLog("error: \(error.localizedDescription)")
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
        // Rebuild without joining "/" components into "//Users/...".
        if shared.first == "/" {
            return shared.dropFirst().reduce(URL(fileURLWithPath: "/")) { partial, component in
                partial.appendingPathComponent(component)
            }
        }
        return shared.dropFirst().reduce(URL(fileURLWithPath: shared[0])) { partial, component in
            partial.appendingPathComponent(component)
        }
    }
}
