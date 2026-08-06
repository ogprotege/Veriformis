import Foundation

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
    let log: String
}

enum WorkbenchError: LocalizedError, Equatable {
    case missingCLI
    case noSources
    case processFailed(stage: String, message: String)
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

            Example from Terminal:
            open /path/to/Veriformis.app
            (Debug builds embed the repo root; uv is probed under ~/.local/bin and /opt/homebrew/bin.)
            """
        case .noSources:
            return "Add at least one source file before compiling."
        case .processFailed(let stage, let message):
            return "Stage \(stage) failed: \(message)"
        case .invalidConfiguration(let message):
            return message
        }
    }
}
