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

enum TaxonomyDiscoveryError: LocalizedError, Equatable, Sendable {
    case invalidKeySet(missing: [String], unexpected: [String])
    case invalidMetadata(String)
    case invalidAxis(String)
    case invalidObjectives([String])
    case commandFailed(exitCode: Int32, message: String)
    case outputTruncated
    case invalidPayload(String)

    var errorDescription: String? {
        switch self {
        case .invalidKeySet(let missing, let unexpected):
            return "Taxonomy discovery keys are invalid (missing: \(missing); unexpected: \(unexpected))."
        case .invalidMetadata(let key):
            return "Taxonomy discovery metadata \(key) is invalid."
        case .invalidAxis(let key):
            return "Taxonomy discovery axis \(key) must contain unique, non-empty identifiers."
        case .invalidObjectives(let objectives):
            return "Taxonomy discovery objectives are unsupported: \(objectives)."
        case .commandFailed(let exitCode, let message):
            let detail = message.isEmpty ? "No diagnostic was returned." : message
            return "Taxonomy discovery failed (exit \(exitCode)): \(detail)"
        case .outputTruncated:
            return "Taxonomy discovery output was truncated."
        case .invalidPayload(let message):
            return "Taxonomy discovery returned invalid JSON: \(message)"
        }
    }
}

/// Strict workbench view of `veriformis taxonomy` discovery.
///
/// The Python registry is authoritative. The workbench accepts the complete v1
/// shape or shows taxonomy help as unavailable; it never fills missing axes
/// from Swift constants or treats an ambiguous `format` value as taxonomy.
struct TaxonomyDiscovery: Decodable, Equatable, Sendable {
    static let expectedKeys: Set<String> = [
        "contract_id",
        "contract_version",
        "schema_id",
        "training_family",
        "objective",
        "semantic_row",
        "physical_container",
        "consumer_profile",
        "loss_policy",
    ]

    let contractID: String
    let contractVersion: String
    let schemaID: String
    let trainingFamilies: [String]
    let objectives: [String]
    let semanticRows: [String]
    let physicalContainers: [String]
    let consumerProfiles: [String]
    let lossPolicies: [String]

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        let payload = try container.decode([String: [String]].self)
        let observedKeys = Set(payload.keys)
        guard observedKeys == Self.expectedKeys else {
            throw TaxonomyDiscoveryError.invalidKeySet(
                missing: Array(Self.expectedKeys.subtracting(observedKeys)).sorted(),
                unexpected: Array(observedKeys.subtracting(Self.expectedKeys)).sorted()
            )
        }

        let contractID = try Self.requireSingleton(
            "contract_id",
            expected: "veriformis.taxonomy",
            in: payload
        )
        let contractVersion = try Self.requireSingleton(
            "contract_version",
            expected: "1",
            in: payload
        )
        let schemaID = try Self.requireSingleton(
            "schema_id",
            expected: "veriformis.taxonomy/v1",
            in: payload
        )
        let trainingFamilies = try Self.requireAxis("training_family", in: payload)
        let objectives = try Self.requireAxis("objective", in: payload)
        let semanticRows = try Self.requireAxis("semantic_row", in: payload)
        let physicalContainers = try Self.requireAxis("physical_container", in: payload)
        let consumerProfiles = try Self.requireAxis("consumer_profile", in: payload)
        let lossPolicies = try Self.requireAxis("loss_policy", in: payload)

        let expectedObjectives = Set(TrainingObjective.allCases.map(\.rawValue))
        guard objectives.count == expectedObjectives.count,
              Set(objectives) == expectedObjectives
        else {
            throw TaxonomyDiscoveryError.invalidObjectives(objectives)
        }

        self.contractID = contractID
        self.contractVersion = contractVersion
        self.schemaID = schemaID
        self.trainingFamilies = trainingFamilies
        self.objectives = objectives
        self.semanticRows = semanticRows
        self.physicalContainers = physicalContainers
        self.consumerProfiles = consumerProfiles
        self.lossPolicies = lossPolicies
    }

    private static func requireSingleton(
        _ key: String,
        expected: String,
        in payload: [String: [String]]
    ) throws -> String {
        guard payload[key] == [expected] else {
            throw TaxonomyDiscoveryError.invalidMetadata(key)
        }
        return expected
    }

    private static func requireAxis(
        _ key: String,
        in payload: [String: [String]]
    ) throws -> [String] {
        guard let identifiers = payload[key],
              !identifiers.isEmpty,
              identifiers.count == Set(identifiers).count,
              identifiers.allSatisfy({ identifier in
                  !identifier.isEmpty
                      && identifier == identifier.trimmingCharacters(in: .whitespacesAndNewlines)
              })
        else {
            throw TaxonomyDiscoveryError.invalidAxis(key)
        }
        return identifiers
    }
}

enum TaxonomyHelpState: Equatable, Sendable {
    case idle
    case loading
    case ready(TaxonomyDiscovery)
    case unavailable(String)
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
    case package

    var id: String { rawValue }

    /// Presentation-only title. Persisted identifiers and CLI arguments remain
    /// the raw values above.
    var title: String {
        switch self {
        case .format:
            return "Lower rows"
        default:
            return rawValue.capitalized
        }
    }

    /// Resolve a persisted stage identifier for presentation without changing
    /// or guessing unknown identifiers from newer workbench versions.
    static func displayTitle(forRawValue rawValue: String) -> String {
        WorkbenchStage(rawValue: rawValue)?.title ?? rawValue
    }

    /// Stages executed by the workbench compile plan (excludes verify).
    static var pipelineStages: [WorkbenchStage] {
        [.parse, .clean, .chunk, .construct, .curate, .split, .format, .validate, .seal]
    }

    /// Complete default workbench run, including immutable transport.
    static var workbenchRunStages: [WorkbenchStage] {
        pipelineStages + [.package]
    }
}

struct StageCommand: Equatable {
    let stage: WorkbenchStage
    let arguments: [String]
}

struct CompileResult: Equatable {
    let workspaceURL: URL
    let bundleURL: URL
    let transportArchiveURL: URL
    let handoffURL: URL?
    let manifestSHA256: String?
    let transportArchiveSHA256: String?
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

    var stageTitle: String {
        WorkbenchStage.displayTitle(forRawValue: stage)
    }

    var summary: String {
        if let exitCode {
            return "Stage \(stageTitle) failed (exit \(exitCode))"
        }
        return "Stage \(stageTitle) failed"
    }
}

enum RunStatus: String, Codable {
    case succeeded
    case failed
    case cancelled
}

/// Durable, factual record of how an interrupted child process was stopped.
struct RunCancellationReceipt: Codable, Equatable {
    let requestedAt: Date
    let stage: String?
    let processIdentifier: Int32?
    let terminationStatus: Int32?
    let terminationEscalated: Bool
    let completedStages: [String]
    let workspaceRetained: Bool
    let outputWasTruncated: Bool

    var stageTitle: String? {
        stage.map(WorkbenchStage.displayTitle(forRawValue:))
    }

    var completedStageTitles: [String] {
        completedStages.map(WorkbenchStage.displayTitle(forRawValue:))
    }
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
    /// Optional so pre-Phase-2 history remains decodable.
    let cancellationReceipt: RunCancellationReceipt?
    /// Optional so pre-Phase-2 history remains decodable.
    let transportArchivePath: String?
    let transportArchiveSHA256: String?

    /// Missing values belong to legacy history records and preserve the
    /// standalone default. Explicitly stored opt-ins remain true.
    var requestsAptusHandoff: Bool {
        writeAptusHandoff ?? false
    }

    var title: String {
        let stamp = RunHistoryEntry.shortDate.string(from: finishedAt)
        return "\(stamp) · \(primarySourceName)"
    }

    var failedStageTitle: String? {
        failedStage.map(WorkbenchStage.displayTitle(forRawValue:))
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
    case cancelled(RunCancellationReceipt)
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

            Preferred launch: ./script/build_and_run.sh
            """
        case .noSources:
            return "Add at least one source file before compiling."
        case .processFailed(let stage, let exitCode, let message):
            let head = message.split(separator: "\n", omittingEmptySubsequences: true).prefix(3).joined(separator: "\n")
            let stageTitle = WorkbenchStage.displayTitle(forRawValue: stage)
            return "Stage \(stageTitle) failed (exit \(exitCode)): \(head)"
        case .cancelled(let receipt):
            let stage = receipt.stageTitle.map { " during \($0)" } ?? ""
            let stop = receipt.terminationEscalated ? "forced termination" : "graceful termination"
            let recovery = receipt.workspaceRetained ? "workspace retained" : "no workspace was created"
            return "Compile cancelled\(stage) (\(stop)); \(recovery)."
        case .invalidConfiguration(let message):
            return message
        }
    }
}
