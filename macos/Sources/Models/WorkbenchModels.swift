import Foundation

enum SidebarDestination: String, CaseIterable, Identifiable {
    case home
    case compile
    case history
    case settings

    var id: String { rawValue }

    var title: String {
        switch self {
        case .home: return "Home"
        case .compile: return "Compile"
        case .history: return "History"
        case .settings: return "Settings"
        }
    }

    var systemImage: String {
        switch self {
        case .home: return "house"
        case .compile: return "shippingbox"
        case .history: return "clock"
        case .settings: return "gearshape"
        }
    }
}

enum TrainingObjective: String, CaseIterable, Identifiable, Codable {
    case fullText = "full_text"
    case continuation = "continuation"
    case sectionReconstruction = "section_reconstruction"
    case beforeAfterTransformation = "before_after_transformation"
    case structuredField = "structured_field"

    var id: String { rawValue }

    var title: String {
        switch self {
        case .fullText: return "Full text"
        case .continuation: return "Continuation"
        case .sectionReconstruction: return "Section reconstruction"
        case .beforeAfterTransformation: return "Before / after"
        case .structuredField: return "Structured field"
        }
    }

    var subtitle: String {
        switch self {
        case .fullText:
            return "Whole cleaned text as training rows"
        case .continuation:
            return "Prompt/completion pairs for next-token style training"
        case .sectionReconstruction:
            return "Rebuild section content from structure"
        case .beforeAfterTransformation:
            return "Paired before/after transformation examples"
        case .structuredField:
            return "Structured field extraction rows"
        }
    }
}

enum WorkbenchStage: String, CaseIterable, Identifiable {
    case parse
    case clean
    case chunk
    case construct
    case curate
    case split
    case format
    case validate
    case seal
    case verify

    var id: String { rawValue }

    var title: String { rawValue.capitalized }

    /// Stages executed by the workbench compile plan (excludes verify).
    static var pipelineStages: [WorkbenchStage] {
        [.parse, .clean, .chunk, .construct, .curate, .split, .format, .validate, .seal]
    }
}

struct StageCommand: Equatable {
    let stage: WorkbenchStage
    let arguments: [String]
}

struct CompileResult: Equatable {
    let workspaceURL: URL
    let bundleURL: URL
    let handoffURL: URL?
    let manifestSHA256: String?
    let assignmentDigest: String?
    let log: String
    let logFileURL: URL?
}

/// Structured failure for debugger UI (Phase 2).
struct CompileFailure: Equatable {
    let stage: String
    let exitCode: Int32?
    let message: String
    let lastLogLines: [String]
    let workspaceURL: URL?
    let logFileURL: URL?

    var summary: String {
        if let exitCode {
            return "Stage \(stage) failed (exit \(exitCode))"
        }
        return "Stage \(stage) failed"
    }
}

enum RunStatus: String, Codable {
    case succeeded
    case failed
}

struct RunHistoryEntry: Identifiable, Codable, Equatable {
    let id: UUID
    let startedAt: Date
    let finishedAt: Date
    let status: RunStatus
    let objective: String
    let primarySourceName: String
    let sourcePaths: [String]
    let workspacePath: String
    let bundlePath: String
    let handoffPath: String?
    let logFilePath: String?
    let manifestSHA256: String?
    let assignmentDigest: String?
    let errorSummary: String?
    /// Optional re-run fidelity (older history entries may omit these).
    let sourceRootPath: String?
    let allowEmptyEvaluation: Bool?
    let writeAptusHandoff: Bool?
    let splitRatioPPM: Int?
    let failedStage: String?
    let exitCode: Int?

    /// Missing values belong to legacy history records and preserve the
    /// standalone default. Explicitly stored opt-ins remain true.
    var requestsAptusHandoff: Bool {
        writeAptusHandoff ?? false
    }

    var title: String {
        let stamp = RunHistoryEntry.shortDate.string(from: finishedAt)
        return "\(stamp) · \(primarySourceName)"
    }

    private static let shortDate: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateStyle = .short
        formatter.timeStyle = .medium
        return formatter
    }()
}

enum WorkbenchError: LocalizedError, Equatable {
    case missingCLI
    case noSources
    case processFailed(stage: String, exitCode: Int32, message: String)
    case invalidConfiguration(String)

    var errorDescription: String? {
        switch self {
        case .missingCLI:
            return """
            Could not locate the veriformis CLI.

            Prerequisites (private beta / development):
            1. From the repo: uv sync
            2. Either put veriformis on PATH, or keep .venv/bin/veriformis after sync, or install uv (Homebrew / ~/.local/bin).
            3. Launch a Debug build from this checkout so the app can find the repo root.

            Overrides:
            • VERIFORMIS_CLI=/absolute/path/to/veriformis
            • VERIFORMIS_DEVELOPMENT_REPOSITORY_ROOT=/absolute/path/to/Veriformis

            Preferred launch: bash macos/scripts/run_workbench.sh
            """
        case .noSources:
            return "Add at least one source file before compiling."
        case .processFailed(let stage, let exitCode, let message):
            let head = message.split(separator: "\n", omittingEmptySubsequences: true).prefix(3).joined(separator: "\n")
            return "Stage \(stage) failed (exit \(exitCode)): \(head)"
        case .invalidConfiguration(let message):
            return message
        }
    }
}
