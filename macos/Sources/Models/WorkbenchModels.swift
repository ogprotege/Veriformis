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

enum ExportSurfaceSchema {
    static let request = "veriformis.export-surface-request/v1"
    static let requestV2 = "veriformis.export-surface-request/v2"
    static let response = "veriformis.export-surface-response/v1"
    static let discovery = "veriformis.export-discovery/v1"
    static let splitJSONLOptions = "veriformis.split-jsonl-options/v1"
}

enum ExportOperation: String, Codable, Equatable, Sendable {
    case discover
    case dryRun = "dry_run"
    case inspect
    case execute
    case verify
}

enum ExportResponseStatus: String, Codable, Equatable, Sendable {
    case ok
    case error
    case cancelled
    case visiblePartial = "visible_partial"
}

enum ExportSourceTrustPolicy: String, Codable, Equatable, Sendable {
    case requireExternalDigest = "require_external_digest"
    case allowSelfConsistent = "allow_self_consistent"
}

enum ExportSourceTrustGrade: String, Codable, Equatable, Sendable {
    case externalDigest = "external_digest"
    case selfConsistent = "self_consistent"
}

enum ExportDeterminismClaim: String, Codable, Equatable, Sendable {
    case portableExactBytes = "portable_exact_bytes"
    case semanticContentOnly = "semantic_content_only"
}

enum ExportOverwritePolicy: String, Codable, Equatable, Sendable {
    case refuse
}

enum ExportMembershipScope: String, Codable, Equatable, Sendable {
    case none
    case train
    case evaluation
    case all
}

enum ExportSurfaceModelError: LocalizedError, Equatable, Sendable {
    case invalidKeySet(model: String, missing: [String], unexpected: [String])
    case invalidValue(String)

    var errorDescription: String? {
        switch self {
        case .invalidKeySet(let model, let missing, let unexpected):
            return "\(model) keys are invalid (missing: \(missing); unexpected: \(unexpected))."
        case .invalidValue(let message):
            return message
        }
    }
}

protocol ExportSurfaceRequest: Encodable, Sendable {
    var operation: ExportOperation { get }
}

extension ExportSurfaceRequest {
    func canonicalJSON() throws -> String {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        let data = try encoder.encode(self)
        guard let json = String(data: data, encoding: .utf8) else {
            throw ExportSurfaceModelError.invalidValue(
                "Export request could not be encoded as UTF-8."
            )
        }
        return json
    }
}

struct SplitJSONLOptions: Encodable, Equatable, Sendable {
    let schemaVersion = ExportSurfaceSchema.splitJSONLOptions
    let trainPartitionName: String
    let evaluationPartitionName: String
    let includeProvenance: Bool

    init(
        trainPartitionName: String,
        evaluationPartitionName: String,
        includeProvenance: Bool
    ) throws {
        try validateSplitJSONLPartitionName(
            trainPartitionName,
            label: "train_partition_name"
        )
        try validateSplitJSONLPartitionName(
            evaluationPartitionName,
            label: "evaluation_partition_name"
        )
        guard trainPartitionName != evaluationPartitionName else {
            throw ExportSurfaceModelError.invalidValue(
                "Split JSONL train and evaluation partition names must differ."
            )
        }
        self.trainPartitionName = trainPartitionName
        self.evaluationPartitionName = evaluationPartitionName
        self.includeProvenance = includeProvenance
    }

    enum CodingKeys: String, CodingKey {
        case schemaVersion = "schema_version"
        case trainPartitionName = "train_partition_name"
        case evaluationPartitionName = "evaluation_partition_name"
        case includeProvenance = "include_provenance"
    }
}

struct ExportDryRunRequest: ExportSurfaceRequest, Equatable {
    let schemaVersion = ExportSurfaceSchema.request
    let operation = ExportOperation.dryRun
    let bundle: String
    let containerID: String
    let containerVersion: Int
    let consumerID: String?
    let consumerProfileVersion: Int?
    let sourceTrustPolicy: ExportSourceTrustPolicy
    let expectedManifestSHA256: String?
    let overwritePolicy = ExportOverwritePolicy.refuse

    init(
        bundle: String,
        containerID: String,
        containerVersion: Int,
        consumerID: String? = nil,
        consumerProfileVersion: Int? = nil,
        sourceTrustPolicy: ExportSourceTrustPolicy,
        expectedManifestSHA256: String?
    ) throws {
        try validateExportSelection(
            bundle: bundle,
            containerID: containerID,
            containerVersion: containerVersion,
            consumerID: consumerID,
            consumerProfileVersion: consumerProfileVersion,
            sourceTrustPolicy: sourceTrustPolicy,
            expectedManifestSHA256: expectedManifestSHA256
        )
        self.bundle = bundle
        self.containerID = containerID
        self.containerVersion = containerVersion
        self.consumerID = consumerID
        self.consumerProfileVersion = consumerProfileVersion
        self.sourceTrustPolicy = sourceTrustPolicy
        self.expectedManifestSHA256 = expectedManifestSHA256
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(schemaVersion, forKey: .schemaVersion)
        try container.encode(operation, forKey: .operation)
        try container.encode(bundle, forKey: .bundle)
        try container.encode(containerID, forKey: .containerID)
        try container.encode(containerVersion, forKey: .containerVersion)
        if let consumerID {
            try container.encode(consumerID, forKey: .consumerID)
        } else {
            try container.encodeNil(forKey: .consumerID)
        }
        if let consumerProfileVersion {
            try container.encode(consumerProfileVersion, forKey: .consumerProfileVersion)
        } else {
            try container.encodeNil(forKey: .consumerProfileVersion)
        }
        try container.encode(sourceTrustPolicy, forKey: .sourceTrustPolicy)
        if let expectedManifestSHA256 {
            try container.encode(expectedManifestSHA256, forKey: .expectedManifestSHA256)
        } else {
            try container.encodeNil(forKey: .expectedManifestSHA256)
        }
        try container.encode(overwritePolicy, forKey: .overwritePolicy)
    }

    enum CodingKeys: String, CodingKey {
        case schemaVersion = "schema_version"
        case operation
        case bundle
        case containerID = "container_id"
        case containerVersion = "container_version"
        case consumerID = "consumer_id"
        case consumerProfileVersion = "consumer_profile_version"
        case sourceTrustPolicy = "source_trust_policy"
        case expectedManifestSHA256 = "expected_manifest_sha256"
        case overwritePolicy = "overwrite_policy"
    }
}

struct ExportDryRunRequestV2: ExportSurfaceRequest, Equatable {
    let schemaVersion = ExportSurfaceSchema.requestV2
    let operation = ExportOperation.dryRun
    let bundle: String
    let containerID: String
    let containerVersion: Int
    let consumerID: String?
    let consumerProfileVersion: Int?
    let sourceTrustPolicy: ExportSourceTrustPolicy
    let expectedManifestSHA256: String?
    let overwritePolicy = ExportOverwritePolicy.refuse
    let containerOptions: SplitJSONLOptions

    init(
        bundle: String,
        containerID: String,
        containerVersion: Int,
        consumerID: String? = nil,
        consumerProfileVersion: Int? = nil,
        sourceTrustPolicy: ExportSourceTrustPolicy,
        expectedManifestSHA256: String?,
        containerOptions: SplitJSONLOptions
    ) throws {
        try validateConfiguredSplitJSONLSelection(
            bundle: bundle,
            containerID: containerID,
            containerVersion: containerVersion,
            consumerID: consumerID,
            consumerProfileVersion: consumerProfileVersion,
            sourceTrustPolicy: sourceTrustPolicy,
            expectedManifestSHA256: expectedManifestSHA256
        )
        self.bundle = bundle
        self.containerID = containerID
        self.containerVersion = containerVersion
        self.consumerID = consumerID
        self.consumerProfileVersion = consumerProfileVersion
        self.sourceTrustPolicy = sourceTrustPolicy
        self.expectedManifestSHA256 = expectedManifestSHA256
        self.containerOptions = containerOptions
    }

    func encode(to encoder: Encoder) throws {
        try encodeSelectedExportRequestV2(
            to: encoder,
            operation: operation,
            bundle: bundle,
            containerID: containerID,
            containerVersion: containerVersion,
            consumerID: consumerID,
            consumerProfileVersion: consumerProfileVersion,
            sourceTrustPolicy: sourceTrustPolicy,
            expectedManifestSHA256: expectedManifestSHA256,
            containerOptions: containerOptions
        )
    }
}

struct ExportInspectRequest: ExportSurfaceRequest, Equatable {
    let schemaVersion = ExportSurfaceSchema.request
    let operation = ExportOperation.inspect
    let destinationRoot: String

    init(destinationRoot: String) throws {
        try validateExportRuntimePath(destinationRoot, label: "destination_root")
        self.destinationRoot = destinationRoot
    }

    enum CodingKeys: String, CodingKey {
        case schemaVersion = "schema_version"
        case operation
        case destinationRoot = "destination_root"
    }
}

struct ExportExecuteRequest: ExportSurfaceRequest, Equatable {
    let schemaVersion = ExportSurfaceSchema.request
    let operation = ExportOperation.execute
    let bundle: String
    let containerID: String
    let containerVersion: Int
    let consumerID: String?
    let consumerProfileVersion: Int?
    let sourceTrustPolicy: ExportSourceTrustPolicy
    let expectedManifestSHA256: String?
    let overwritePolicy = ExportOverwritePolicy.refuse
    let destinationRoot: String
    let expectedExportPlanID: String

    init(
        bundle: String,
        containerID: String,
        containerVersion: Int,
        consumerID: String? = nil,
        consumerProfileVersion: Int? = nil,
        sourceTrustPolicy: ExportSourceTrustPolicy,
        expectedManifestSHA256: String?,
        destinationRoot: String,
        expectedExportPlanID: String
    ) throws {
        try validateExportSelection(
            bundle: bundle,
            containerID: containerID,
            containerVersion: containerVersion,
            consumerID: consumerID,
            consumerProfileVersion: consumerProfileVersion,
            sourceTrustPolicy: sourceTrustPolicy,
            expectedManifestSHA256: expectedManifestSHA256
        )
        try validateExportRuntimePath(destinationRoot, label: "destination_root")
        try validateExportID(expectedExportPlanID, kind: "export-plan")
        self.bundle = bundle
        self.containerID = containerID
        self.containerVersion = containerVersion
        self.consumerID = consumerID
        self.consumerProfileVersion = consumerProfileVersion
        self.sourceTrustPolicy = sourceTrustPolicy
        self.expectedManifestSHA256 = expectedManifestSHA256
        self.destinationRoot = destinationRoot
        self.expectedExportPlanID = expectedExportPlanID
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(schemaVersion, forKey: .schemaVersion)
        try container.encode(operation, forKey: .operation)
        try container.encode(bundle, forKey: .bundle)
        try container.encode(containerID, forKey: .containerID)
        try container.encode(containerVersion, forKey: .containerVersion)
        if let consumerID {
            try container.encode(consumerID, forKey: .consumerID)
        } else {
            try container.encodeNil(forKey: .consumerID)
        }
        if let consumerProfileVersion {
            try container.encode(consumerProfileVersion, forKey: .consumerProfileVersion)
        } else {
            try container.encodeNil(forKey: .consumerProfileVersion)
        }
        try container.encode(sourceTrustPolicy, forKey: .sourceTrustPolicy)
        if let expectedManifestSHA256 {
            try container.encode(expectedManifestSHA256, forKey: .expectedManifestSHA256)
        } else {
            try container.encodeNil(forKey: .expectedManifestSHA256)
        }
        try container.encode(overwritePolicy, forKey: .overwritePolicy)
        try container.encode(destinationRoot, forKey: .destinationRoot)
        try container.encode(expectedExportPlanID, forKey: .expectedExportPlanID)
    }

    enum CodingKeys: String, CodingKey {
        case schemaVersion = "schema_version"
        case operation
        case bundle
        case containerID = "container_id"
        case containerVersion = "container_version"
        case consumerID = "consumer_id"
        case consumerProfileVersion = "consumer_profile_version"
        case sourceTrustPolicy = "source_trust_policy"
        case expectedManifestSHA256 = "expected_manifest_sha256"
        case overwritePolicy = "overwrite_policy"
        case destinationRoot = "destination_root"
        case expectedExportPlanID = "expected_export_plan_id"
    }
}

struct ExportExecuteRequestV2: ExportSurfaceRequest, Equatable {
    let schemaVersion = ExportSurfaceSchema.requestV2
    let operation = ExportOperation.execute
    let bundle: String
    let containerID: String
    let containerVersion: Int
    let consumerID: String?
    let consumerProfileVersion: Int?
    let sourceTrustPolicy: ExportSourceTrustPolicy
    let expectedManifestSHA256: String?
    let overwritePolicy = ExportOverwritePolicy.refuse
    let destinationRoot: String
    let expectedExportPlanID: String
    let containerOptions: SplitJSONLOptions

    init(
        bundle: String,
        containerID: String,
        containerVersion: Int,
        consumerID: String? = nil,
        consumerProfileVersion: Int? = nil,
        sourceTrustPolicy: ExportSourceTrustPolicy,
        expectedManifestSHA256: String?,
        destinationRoot: String,
        expectedExportPlanID: String,
        containerOptions: SplitJSONLOptions
    ) throws {
        try validateConfiguredSplitJSONLSelection(
            bundle: bundle,
            containerID: containerID,
            containerVersion: containerVersion,
            consumerID: consumerID,
            consumerProfileVersion: consumerProfileVersion,
            sourceTrustPolicy: sourceTrustPolicy,
            expectedManifestSHA256: expectedManifestSHA256
        )
        try validateExportRuntimePath(destinationRoot, label: "destination_root")
        try validateExportID(expectedExportPlanID, kind: "export-plan")
        self.bundle = bundle
        self.containerID = containerID
        self.containerVersion = containerVersion
        self.consumerID = consumerID
        self.consumerProfileVersion = consumerProfileVersion
        self.sourceTrustPolicy = sourceTrustPolicy
        self.expectedManifestSHA256 = expectedManifestSHA256
        self.destinationRoot = destinationRoot
        self.expectedExportPlanID = expectedExportPlanID
        self.containerOptions = containerOptions
    }

    func encode(to encoder: Encoder) throws {
        try encodeSelectedExportRequestV2(
            to: encoder,
            operation: operation,
            bundle: bundle,
            containerID: containerID,
            containerVersion: containerVersion,
            consumerID: consumerID,
            consumerProfileVersion: consumerProfileVersion,
            sourceTrustPolicy: sourceTrustPolicy,
            expectedManifestSHA256: expectedManifestSHA256,
            containerOptions: containerOptions,
            destinationRoot: destinationRoot,
            expectedExportPlanID: expectedExportPlanID
        )
    }
}

struct ExportVerifyRequest: ExportSurfaceRequest, Equatable {
    let schemaVersion = ExportSurfaceSchema.request
    let operation = ExportOperation.verify
    let bundle: String
    let containerID: String
    let containerVersion: Int
    let consumerID: String?
    let consumerProfileVersion: Int?
    let sourceTrustPolicy: ExportSourceTrustPolicy
    let expectedManifestSHA256: String?
    let overwritePolicy = ExportOverwritePolicy.refuse
    let destinationRoot: String
    let expectedExportPlanID: String

    init(
        bundle: String,
        containerID: String,
        containerVersion: Int,
        consumerID: String? = nil,
        consumerProfileVersion: Int? = nil,
        sourceTrustPolicy: ExportSourceTrustPolicy,
        expectedManifestSHA256: String?,
        destinationRoot: String,
        expectedExportPlanID: String
    ) throws {
        try validateExportSelection(
            bundle: bundle,
            containerID: containerID,
            containerVersion: containerVersion,
            consumerID: consumerID,
            consumerProfileVersion: consumerProfileVersion,
            sourceTrustPolicy: sourceTrustPolicy,
            expectedManifestSHA256: expectedManifestSHA256
        )
        try validateExportRuntimePath(destinationRoot, label: "destination_root")
        try validateExportID(expectedExportPlanID, kind: "export-plan")
        self.bundle = bundle
        self.containerID = containerID
        self.containerVersion = containerVersion
        self.consumerID = consumerID
        self.consumerProfileVersion = consumerProfileVersion
        self.sourceTrustPolicy = sourceTrustPolicy
        self.expectedManifestSHA256 = expectedManifestSHA256
        self.destinationRoot = destinationRoot
        self.expectedExportPlanID = expectedExportPlanID
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(schemaVersion, forKey: .schemaVersion)
        try container.encode(operation, forKey: .operation)
        try container.encode(bundle, forKey: .bundle)
        try container.encode(containerID, forKey: .containerID)
        try container.encode(containerVersion, forKey: .containerVersion)
        if let consumerID {
            try container.encode(consumerID, forKey: .consumerID)
        } else {
            try container.encodeNil(forKey: .consumerID)
        }
        if let consumerProfileVersion {
            try container.encode(consumerProfileVersion, forKey: .consumerProfileVersion)
        } else {
            try container.encodeNil(forKey: .consumerProfileVersion)
        }
        try container.encode(sourceTrustPolicy, forKey: .sourceTrustPolicy)
        if let expectedManifestSHA256 {
            try container.encode(expectedManifestSHA256, forKey: .expectedManifestSHA256)
        } else {
            try container.encodeNil(forKey: .expectedManifestSHA256)
        }
        try container.encode(overwritePolicy, forKey: .overwritePolicy)
        try container.encode(destinationRoot, forKey: .destinationRoot)
        try container.encode(expectedExportPlanID, forKey: .expectedExportPlanID)
    }

    enum CodingKeys: String, CodingKey {
        case schemaVersion = "schema_version"
        case operation
        case bundle
        case containerID = "container_id"
        case containerVersion = "container_version"
        case consumerID = "consumer_id"
        case consumerProfileVersion = "consumer_profile_version"
        case sourceTrustPolicy = "source_trust_policy"
        case expectedManifestSHA256 = "expected_manifest_sha256"
        case overwritePolicy = "overwrite_policy"
        case destinationRoot = "destination_root"
        case expectedExportPlanID = "expected_export_plan_id"
    }
}

struct ExportVerifyRequestV2: ExportSurfaceRequest, Equatable {
    let schemaVersion = ExportSurfaceSchema.requestV2
    let operation = ExportOperation.verify
    let bundle: String
    let containerID: String
    let containerVersion: Int
    let consumerID: String?
    let consumerProfileVersion: Int?
    let sourceTrustPolicy: ExportSourceTrustPolicy
    let expectedManifestSHA256: String?
    let overwritePolicy = ExportOverwritePolicy.refuse
    let destinationRoot: String
    let expectedExportPlanID: String
    let containerOptions: SplitJSONLOptions

    init(
        bundle: String,
        containerID: String,
        containerVersion: Int,
        consumerID: String? = nil,
        consumerProfileVersion: Int? = nil,
        sourceTrustPolicy: ExportSourceTrustPolicy,
        expectedManifestSHA256: String?,
        destinationRoot: String,
        expectedExportPlanID: String,
        containerOptions: SplitJSONLOptions
    ) throws {
        try validateConfiguredSplitJSONLSelection(
            bundle: bundle,
            containerID: containerID,
            containerVersion: containerVersion,
            consumerID: consumerID,
            consumerProfileVersion: consumerProfileVersion,
            sourceTrustPolicy: sourceTrustPolicy,
            expectedManifestSHA256: expectedManifestSHA256
        )
        try validateExportRuntimePath(destinationRoot, label: "destination_root")
        try validateExportID(expectedExportPlanID, kind: "export-plan")
        self.bundle = bundle
        self.containerID = containerID
        self.containerVersion = containerVersion
        self.consumerID = consumerID
        self.consumerProfileVersion = consumerProfileVersion
        self.sourceTrustPolicy = sourceTrustPolicy
        self.expectedManifestSHA256 = expectedManifestSHA256
        self.destinationRoot = destinationRoot
        self.expectedExportPlanID = expectedExportPlanID
        self.containerOptions = containerOptions
    }

    func encode(to encoder: Encoder) throws {
        try encodeSelectedExportRequestV2(
            to: encoder,
            operation: operation,
            bundle: bundle,
            containerID: containerID,
            containerVersion: containerVersion,
            consumerID: consumerID,
            consumerProfileVersion: consumerProfileVersion,
            sourceTrustPolicy: sourceTrustPolicy,
            expectedManifestSHA256: expectedManifestSHA256,
            containerOptions: containerOptions,
            destinationRoot: destinationRoot,
            expectedExportPlanID: expectedExportPlanID
        )
    }
}

struct ExportSurfaceError: Decodable, Equatable, Sendable {
    let code: String
    let message: String

    init(from decoder: Decoder) throws {
        try decoder.requireExactExportKeys(["code", "message"], model: "export error")
        let container = try decoder.container(keyedBy: CodingKeys.self)
        code = try container.decode(String.self, forKey: .code)
        message = try container.decode(String.self, forKey: .message)
        guard !code.isEmpty else {
            throw ExportSurfaceModelError.invalidValue("Export error code cannot be empty.")
        }
    }

    enum CodingKeys: String, CodingKey {
        case code
        case message
    }
}

struct ExportContainerProfileSummary: Decodable, Equatable, Sendable {
    let schemaVersion: String
    let containerProfileID: String
    let containerID: String
    let containerVersion: Int
    let determinismClaim: ExportDeterminismClaim

    init(from decoder: Decoder) throws {
        try decoder.requireExactExportKeys(
            ["schema_version", "container_profile_id", "container_id", "container_version", "determinism_claim"],
            model: "export container profile"
        )
        let container = try decoder.container(keyedBy: CodingKeys.self)
        schemaVersion = try container.decode(String.self, forKey: .schemaVersion)
        containerProfileID = try container.decode(String.self, forKey: .containerProfileID)
        containerID = try container.decode(String.self, forKey: .containerID)
        containerVersion = try container.decode(Int.self, forKey: .containerVersion)
        determinismClaim = try container.decode(ExportDeterminismClaim.self, forKey: .determinismClaim)
        try requireExportSchema(
            schemaVersion,
            expected: "veriformis.export-container-profile/v1",
            model: "export container profile"
        )
        guard containerVersion > 0 else {
            throw ExportSurfaceModelError.invalidValue("Export container version must be positive.")
        }
    }

    enum CodingKeys: String, CodingKey {
        case schemaVersion = "schema_version"
        case containerProfileID = "container_profile_id"
        case containerID = "container_id"
        case containerVersion = "container_version"
        case determinismClaim = "determinism_claim"
    }
}

struct ExportConsumerProfileSummary: Decodable, Equatable, Sendable {
    let schemaVersion: String
    let consumerProfileID: String
    let consumerID: String
    let profileVersion: Int
    let acceptedRowSchemas: [String]

    init(from decoder: Decoder) throws {
        try decoder.requireExactExportKeys(
            ["schema_version", "consumer_profile_id", "consumer_id", "profile_version", "accepted_row_schemas"],
            model: "export consumer profile"
        )
        let container = try decoder.container(keyedBy: CodingKeys.self)
        schemaVersion = try container.decode(String.self, forKey: .schemaVersion)
        consumerProfileID = try container.decode(String.self, forKey: .consumerProfileID)
        consumerID = try container.decode(String.self, forKey: .consumerID)
        profileVersion = try container.decode(Int.self, forKey: .profileVersion)
        acceptedRowSchemas = try container.decode([String].self, forKey: .acceptedRowSchemas)
        try requireExportSchema(
            schemaVersion,
            expected: "veriformis.export-consumer-profile/v1",
            model: "export consumer profile"
        )
        guard profileVersion > 0, !acceptedRowSchemas.isEmpty else {
            throw ExportSurfaceModelError.invalidValue("Export consumer profile is empty or invalid.")
        }
    }

    enum CodingKeys: String, CodingKey {
        case schemaVersion = "schema_version"
        case consumerProfileID = "consumer_profile_id"
        case consumerID = "consumer_id"
        case profileVersion = "profile_version"
        case acceptedRowSchemas = "accepted_row_schemas"
    }
}

struct ExportDependencySummary: Decodable, Equatable, Sendable {
    let schemaVersion: String
    let dependencyID: String
    let dependencyName: String
    let dependencyVersion: String
    let dependencyRole: String

    init(from decoder: Decoder) throws {
        try decoder.requireExactExportKeys(
            ["schema_version", "dependency_id", "dependency_name", "dependency_version", "dependency_role"],
            model: "export dependency"
        )
        let container = try decoder.container(keyedBy: CodingKeys.self)
        schemaVersion = try container.decode(String.self, forKey: .schemaVersion)
        dependencyID = try container.decode(String.self, forKey: .dependencyID)
        dependencyName = try container.decode(String.self, forKey: .dependencyName)
        dependencyVersion = try container.decode(String.self, forKey: .dependencyVersion)
        dependencyRole = try container.decode(String.self, forKey: .dependencyRole)
        try requireExportSchema(
            schemaVersion,
            expected: "veriformis.export-dependency-binding/v1",
            model: "export dependency"
        )
    }

    enum CodingKeys: String, CodingKey {
        case schemaVersion = "schema_version"
        case dependencyID = "dependency_id"
        case dependencyName = "dependency_name"
        case dependencyVersion = "dependency_version"
        case dependencyRole = "dependency_role"
    }
}

struct ExportProfileDescriptorSummary: Decodable, Equatable, Sendable {
    let containerProfile: ExportContainerProfileSummary
    let consumerProfile: ExportConsumerProfileSummary?
    let dependencies: [ExportDependencySummary]
    let overwritePolicies: [ExportOverwritePolicy]
    let supportedRowSchemas: [String]

    init(from decoder: Decoder) throws {
        try decoder.requireExactExportKeys(
            ["container_profile", "consumer_profile", "dependencies", "overwrite_policies", "supported_row_schemas"],
            model: "export profile descriptor"
        )
        let container = try decoder.container(keyedBy: CodingKeys.self)
        containerProfile = try container.decode(ExportContainerProfileSummary.self, forKey: .containerProfile)
        consumerProfile = try container.decodeIfPresent(ExportConsumerProfileSummary.self, forKey: .consumerProfile)
        dependencies = try container.decode([ExportDependencySummary].self, forKey: .dependencies)
        overwritePolicies = try container.decode([ExportOverwritePolicy].self, forKey: .overwritePolicies)
        supportedRowSchemas = try container.decode([String].self, forKey: .supportedRowSchemas)
        guard overwritePolicies == [.refuse], !dependencies.isEmpty, !supportedRowSchemas.isEmpty else {
            throw ExportSurfaceModelError.invalidValue("Export profile descriptor is empty or permits overwrite.")
        }
    }

    enum CodingKeys: String, CodingKey {
        case containerProfile = "container_profile"
        case consumerProfile = "consumer_profile"
        case dependencies
        case overwritePolicies = "overwrite_policies"
        case supportedRowSchemas = "supported_row_schemas"
    }
}

protocol ExportSurfaceResult: Decodable, Equatable, Sendable {
    static var operation: ExportOperation { get }
}

struct ExportDiscovery: ExportSurfaceResult {
    static let operation = ExportOperation.discover

    let schemaVersion: String
    let profiles: [ExportProfileDescriptorSummary]

    init(from decoder: Decoder) throws {
        try decoder.requireExactExportKeys(["profiles", "schema_version"], model: "export discovery")
        let container = try decoder.container(keyedBy: CodingKeys.self)
        schemaVersion = try container.decode(String.self, forKey: .schemaVersion)
        profiles = try container.decode([ExportProfileDescriptorSummary].self, forKey: .profiles)
        try requireExportSchema(
            schemaVersion,
            expected: ExportSurfaceSchema.discovery,
            model: "export discovery"
        )
    }

    enum CodingKeys: String, CodingKey {
        case schemaVersion = "schema_version"
        case profiles
    }
}

struct ExportFilePlanSummary: Decodable, Equatable, Sendable {
    let expectedByteSize: Int?
    let expectedSHA256: String?
    let filePlanID: String
    let mediaType: String
    let membershipScope: ExportMembershipScope
    let path: String
    let recordCount: Int?
    let role: String
    let semanticContentSHA256: String?

    init(from decoder: Decoder) throws {
        try decoder.requireExactExportKeys(
            ["expected_byte_size", "expected_sha256", "file_plan_id", "media_type", "membership_scope", "path", "record_count", "role", "semantic_content_sha256"],
            model: "export file plan summary"
        )
        let container = try decoder.container(keyedBy: CodingKeys.self)
        expectedByteSize = try container.decodeIfPresent(Int.self, forKey: .expectedByteSize)
        expectedSHA256 = try container.decodeIfPresent(String.self, forKey: .expectedSHA256)
        filePlanID = try container.decode(String.self, forKey: .filePlanID)
        mediaType = try container.decode(String.self, forKey: .mediaType)
        membershipScope = try container.decode(ExportMembershipScope.self, forKey: .membershipScope)
        path = try container.decode(String.self, forKey: .path)
        recordCount = try container.decodeIfPresent(Int.self, forKey: .recordCount)
        role = try container.decode(String.self, forKey: .role)
        semanticContentSHA256 = try container.decodeIfPresent(String.self, forKey: .semanticContentSHA256)
    }

    enum CodingKeys: String, CodingKey {
        case expectedByteSize = "expected_byte_size"
        case expectedSHA256 = "expected_sha256"
        case filePlanID = "file_plan_id"
        case mediaType = "media_type"
        case membershipScope = "membership_scope"
        case path
        case recordCount = "record_count"
        case role
        case semanticContentSHA256 = "semantic_content_sha256"
    }
}

struct ExportPlanSummary: Decodable, Equatable, Sendable {
    let canonicalSHA256: String
    let consumerProfileID: String?
    let containerProfileID: String
    let evaluationRecordCount: Int
    let exportPlanID: String
    let files: [ExportFilePlanSummary]
    let membershipProjectionID: String
    let overwritePolicy: ExportOverwritePolicy
    let rowSchema: String
    let rowSetID: String
    let sourceBundleID: String
    let sourceManifestSHA256: String
    let sourceTrustGrade: ExportSourceTrustGrade
    let sourceTrustPolicy: ExportSourceTrustPolicy
    let totalRecordCount: Int
    let trainRecordCount: Int

    init(from decoder: Decoder) throws {
        try decoder.requireExactExportKeys(
            ["canonical_sha256", "consumer_profile_id", "container_profile_id", "evaluation_record_count", "export_plan_id", "files", "membership_projection_id", "overwrite_policy", "row_schema", "row_set_id", "source_bundle_id", "source_manifest_sha256", "source_trust_grade", "source_trust_policy", "total_record_count", "train_record_count"],
            model: "export plan summary"
        )
        let container = try decoder.container(keyedBy: CodingKeys.self)
        canonicalSHA256 = try container.decode(String.self, forKey: .canonicalSHA256)
        consumerProfileID = try container.decodeIfPresent(String.self, forKey: .consumerProfileID)
        containerProfileID = try container.decode(String.self, forKey: .containerProfileID)
        evaluationRecordCount = try container.decode(Int.self, forKey: .evaluationRecordCount)
        exportPlanID = try container.decode(String.self, forKey: .exportPlanID)
        files = try container.decode([ExportFilePlanSummary].self, forKey: .files)
        membershipProjectionID = try container.decode(String.self, forKey: .membershipProjectionID)
        overwritePolicy = try container.decode(ExportOverwritePolicy.self, forKey: .overwritePolicy)
        rowSchema = try container.decode(String.self, forKey: .rowSchema)
        rowSetID = try container.decode(String.self, forKey: .rowSetID)
        sourceBundleID = try container.decode(String.self, forKey: .sourceBundleID)
        sourceManifestSHA256 = try container.decode(String.self, forKey: .sourceManifestSHA256)
        sourceTrustGrade = try container.decode(ExportSourceTrustGrade.self, forKey: .sourceTrustGrade)
        sourceTrustPolicy = try container.decode(ExportSourceTrustPolicy.self, forKey: .sourceTrustPolicy)
        totalRecordCount = try container.decode(Int.self, forKey: .totalRecordCount)
        trainRecordCount = try container.decode(Int.self, forKey: .trainRecordCount)
        guard evaluationRecordCount >= 0,
              trainRecordCount > 0,
              totalRecordCount == trainRecordCount + evaluationRecordCount,
              !files.isEmpty
        else {
            throw ExportSurfaceModelError.invalidValue("Export plan summary record counts are invalid.")
        }
    }

    enum CodingKeys: String, CodingKey {
        case canonicalSHA256 = "canonical_sha256"
        case consumerProfileID = "consumer_profile_id"
        case containerProfileID = "container_profile_id"
        case evaluationRecordCount = "evaluation_record_count"
        case exportPlanID = "export_plan_id"
        case files
        case membershipProjectionID = "membership_projection_id"
        case overwritePolicy = "overwrite_policy"
        case rowSchema = "row_schema"
        case rowSetID = "row_set_id"
        case sourceBundleID = "source_bundle_id"
        case sourceManifestSHA256 = "source_manifest_sha256"
        case sourceTrustGrade = "source_trust_grade"
        case sourceTrustPolicy = "source_trust_policy"
        case totalRecordCount = "total_record_count"
        case trainRecordCount = "train_record_count"
    }
}

struct ExportDestinationFileSummary: Decodable, Equatable, Sendable {
    let schemaVersion: String
    let destinationFileID: String
    let filePlanID: String
    let path: String
    let role: String
    let mediaType: String
    let membershipScope: ExportMembershipScope
    let recordCount: Int?
    let semanticContentSHA256: String?
    let sha256: String
    let byteSize: Int

    init(from decoder: Decoder) throws {
        try decoder.requireExactExportKeys(
            ["schema_version", "destination_file_id", "file_plan_id", "path", "role", "media_type", "membership_scope", "record_count", "semantic_content_sha256", "sha256", "byte_size"],
            model: "export destination file summary"
        )
        let container = try decoder.container(keyedBy: CodingKeys.self)
        schemaVersion = try container.decode(String.self, forKey: .schemaVersion)
        destinationFileID = try container.decode(String.self, forKey: .destinationFileID)
        filePlanID = try container.decode(String.self, forKey: .filePlanID)
        path = try container.decode(String.self, forKey: .path)
        role = try container.decode(String.self, forKey: .role)
        mediaType = try container.decode(String.self, forKey: .mediaType)
        membershipScope = try container.decode(ExportMembershipScope.self, forKey: .membershipScope)
        recordCount = try container.decodeIfPresent(Int.self, forKey: .recordCount)
        semanticContentSHA256 = try container.decodeIfPresent(String.self, forKey: .semanticContentSHA256)
        sha256 = try container.decode(String.self, forKey: .sha256)
        byteSize = try container.decode(Int.self, forKey: .byteSize)
        try requireExportSchema(
            schemaVersion,
            expected: "veriformis.export-destination-file-binding/v1",
            model: "export destination file summary"
        )
        guard byteSize >= 0 else {
            throw ExportSurfaceModelError.invalidValue("Export destination byte size cannot be negative.")
        }
    }

    enum CodingKeys: String, CodingKey {
        case schemaVersion = "schema_version"
        case destinationFileID = "destination_file_id"
        case filePlanID = "file_plan_id"
        case path
        case role
        case mediaType = "media_type"
        case membershipScope = "membership_scope"
        case recordCount = "record_count"
        case semanticContentSHA256 = "semantic_content_sha256"
        case sha256
        case byteSize = "byte_size"
    }
}

struct ExportReceiptSummary: Decodable, Equatable, Sendable {
    let canonicalSHA256: String
    let exportPlanID: String
    let exportReceiptID: String
    let files: [ExportDestinationFileSummary]
    let outputContentRootSHA256: String

    init(from decoder: Decoder) throws {
        try decoder.requireExactExportKeys(
            ["canonical_sha256", "export_plan_id", "export_receipt_id", "files", "output_content_root_sha256"],
            model: "export receipt summary"
        )
        let container = try decoder.container(keyedBy: CodingKeys.self)
        canonicalSHA256 = try container.decode(String.self, forKey: .canonicalSHA256)
        exportPlanID = try container.decode(String.self, forKey: .exportPlanID)
        exportReceiptID = try container.decode(String.self, forKey: .exportReceiptID)
        files = try container.decode([ExportDestinationFileSummary].self, forKey: .files)
        outputContentRootSHA256 = try container.decode(String.self, forKey: .outputContentRootSHA256)
        guard !files.isEmpty else {
            throw ExportSurfaceModelError.invalidValue("Export receipt summary cannot be empty.")
        }
    }

    enum CodingKeys: String, CodingKey {
        case canonicalSHA256 = "canonical_sha256"
        case exportPlanID = "export_plan_id"
        case exportReceiptID = "export_receipt_id"
        case files
        case outputContentRootSHA256 = "output_content_root_sha256"
    }
}

struct ExportVerificationSummary: Decodable, Equatable, Sendable {
    let schemaVersion: String
    let exportVerificationID: String
    let exportReceiptID: String
    let exportPlanID: String
    let sourceBundleID: String
    let sourceManifestSHA256: String
    let sourceContentRootSHA256: String
    let sourceVerificationID: String
    let sourceTrustGrade: ExportSourceTrustGrade
    let datasetSnapshotID: String
    let validationReportID: String
    let splitResultID: String
    let rowSetID: String
    let rowSchema: String
    let containerProfileID: String
    let consumerProfileID: String?
    let membershipProjectionID: String
    let determinismClaim: ExportDeterminismClaim
    let outputContentRootSHA256: String
    let outputFileCount: Int
    let declaredRecordCount: Int
    let canonicalSHA256: String

    init(from decoder: Decoder) throws {
        try decoder.requireExactExportKeys(
            ["schema_version", "export_verification_id", "export_receipt_id", "export_plan_id", "source_bundle_id", "source_manifest_sha256", "source_content_root_sha256", "source_verification_id", "source_trust_grade", "dataset_snapshot_id", "validation_report_id", "split_result_id", "row_set_id", "row_schema", "container_profile_id", "consumer_profile_id", "membership_projection_id", "determinism_claim", "output_content_root_sha256", "output_file_count", "declared_record_count", "canonical_sha256"],
            model: "export verification summary"
        )
        let container = try decoder.container(keyedBy: CodingKeys.self)
        schemaVersion = try container.decode(String.self, forKey: .schemaVersion)
        exportVerificationID = try container.decode(String.self, forKey: .exportVerificationID)
        exportReceiptID = try container.decode(String.self, forKey: .exportReceiptID)
        exportPlanID = try container.decode(String.self, forKey: .exportPlanID)
        sourceBundleID = try container.decode(String.self, forKey: .sourceBundleID)
        sourceManifestSHA256 = try container.decode(String.self, forKey: .sourceManifestSHA256)
        sourceContentRootSHA256 = try container.decode(String.self, forKey: .sourceContentRootSHA256)
        sourceVerificationID = try container.decode(String.self, forKey: .sourceVerificationID)
        sourceTrustGrade = try container.decode(ExportSourceTrustGrade.self, forKey: .sourceTrustGrade)
        datasetSnapshotID = try container.decode(String.self, forKey: .datasetSnapshotID)
        validationReportID = try container.decode(String.self, forKey: .validationReportID)
        splitResultID = try container.decode(String.self, forKey: .splitResultID)
        rowSetID = try container.decode(String.self, forKey: .rowSetID)
        rowSchema = try container.decode(String.self, forKey: .rowSchema)
        containerProfileID = try container.decode(String.self, forKey: .containerProfileID)
        consumerProfileID = try container.decodeIfPresent(String.self, forKey: .consumerProfileID)
        membershipProjectionID = try container.decode(String.self, forKey: .membershipProjectionID)
        determinismClaim = try container.decode(ExportDeterminismClaim.self, forKey: .determinismClaim)
        outputContentRootSHA256 = try container.decode(String.self, forKey: .outputContentRootSHA256)
        outputFileCount = try container.decode(Int.self, forKey: .outputFileCount)
        declaredRecordCount = try container.decode(Int.self, forKey: .declaredRecordCount)
        canonicalSHA256 = try container.decode(String.self, forKey: .canonicalSHA256)
        try requireExportSchema(
            schemaVersion,
            expected: "veriformis.export-verification/v1",
            model: "export verification summary"
        )
        guard outputFileCount > 0, declaredRecordCount > 0 else {
            throw ExportSurfaceModelError.invalidValue("Export verification counts must be positive.")
        }
    }

    enum CodingKeys: String, CodingKey {
        case schemaVersion = "schema_version"
        case exportVerificationID = "export_verification_id"
        case exportReceiptID = "export_receipt_id"
        case exportPlanID = "export_plan_id"
        case sourceBundleID = "source_bundle_id"
        case sourceManifestSHA256 = "source_manifest_sha256"
        case sourceContentRootSHA256 = "source_content_root_sha256"
        case sourceVerificationID = "source_verification_id"
        case sourceTrustGrade = "source_trust_grade"
        case datasetSnapshotID = "dataset_snapshot_id"
        case validationReportID = "validation_report_id"
        case splitResultID = "split_result_id"
        case rowSetID = "row_set_id"
        case rowSchema = "row_schema"
        case containerProfileID = "container_profile_id"
        case consumerProfileID = "consumer_profile_id"
        case membershipProjectionID = "membership_projection_id"
        case determinismClaim = "determinism_claim"
        case outputContentRootSHA256 = "output_content_root_sha256"
        case outputFileCount = "output_file_count"
        case declaredRecordCount = "declared_record_count"
        case canonicalSHA256 = "canonical_sha256"
    }
}

struct ExportDryRunResult: ExportSurfaceResult {
    static let operation = ExportOperation.dryRun
    let plan: ExportPlanSummary

    init(from decoder: Decoder) throws {
        try decoder.requireExactExportKeys(["plan"], model: "export dry-run result")
        plan = try decoder.container(keyedBy: CodingKeys.self).decode(ExportPlanSummary.self, forKey: .plan)
    }

    enum CodingKeys: CodingKey { case plan }
}

struct ExportInspectionResult: ExportSurfaceResult {
    static let operation = ExportOperation.inspect
    let destinationRoot: String
    let inspectionScope: String
    let plan: ExportPlanSummary
    let receipt: ExportReceiptSummary

    init(from decoder: Decoder) throws {
        try decoder.requireExactExportKeys(
            ["destination_root", "inspection_scope", "plan", "receipt"],
            model: "export inspection result"
        )
        let container = try decoder.container(keyedBy: CodingKeys.self)
        destinationRoot = try container.decode(String.self, forKey: .destinationRoot)
        inspectionScope = try container.decode(String.self, forKey: .inspectionScope)
        plan = try container.decode(ExportPlanSummary.self, forKey: .plan)
        receipt = try container.decode(ExportReceiptSummary.self, forKey: .receipt)
        guard inspectionScope == "self_described_physical" else {
            throw ExportSurfaceModelError.invalidValue("Export inspection scope is unsupported.")
        }
    }

    enum CodingKeys: String, CodingKey {
        case destinationRoot = "destination_root"
        case inspectionScope = "inspection_scope"
        case plan
        case receipt
    }
}

struct ExportExecutionResult: ExportSurfaceResult {
    static let operation = ExportOperation.execute
    let destinationRoot: String
    let durabilityWarning: String?
    let plan: ExportPlanSummary
    let receipt: ExportReceiptSummary
    let verification: ExportVerificationSummary

    init(from decoder: Decoder) throws {
        try decoder.requireExactExportKeys(
            ["destination_root", "durability_warning", "plan", "receipt", "verification"],
            model: "export execution result"
        )
        let container = try decoder.container(keyedBy: CodingKeys.self)
        destinationRoot = try container.decode(String.self, forKey: .destinationRoot)
        durabilityWarning = try container.decodeIfPresent(String.self, forKey: .durabilityWarning)
        plan = try container.decode(ExportPlanSummary.self, forKey: .plan)
        receipt = try container.decode(ExportReceiptSummary.self, forKey: .receipt)
        verification = try container.decode(ExportVerificationSummary.self, forKey: .verification)
    }

    enum CodingKeys: String, CodingKey {
        case destinationRoot = "destination_root"
        case durabilityWarning = "durability_warning"
        case plan
        case receipt
        case verification
    }
}

struct ExportVerifyResult: ExportSurfaceResult {
    static let operation = ExportOperation.verify
    let destinationRoot: String
    let plan: ExportPlanSummary
    let receipt: ExportReceiptSummary
    let verification: ExportVerificationSummary

    init(from decoder: Decoder) throws {
        try decoder.requireExactExportKeys(
            ["destination_root", "plan", "receipt", "verification"],
            model: "export verification result"
        )
        let container = try decoder.container(keyedBy: CodingKeys.self)
        destinationRoot = try container.decode(String.self, forKey: .destinationRoot)
        plan = try container.decode(ExportPlanSummary.self, forKey: .plan)
        receipt = try container.decode(ExportReceiptSummary.self, forKey: .receipt)
        verification = try container.decode(ExportVerificationSummary.self, forKey: .verification)
    }

    enum CodingKeys: String, CodingKey {
        case destinationRoot = "destination_root"
        case plan
        case receipt
        case verification
    }
}

struct ExportSurfaceResponse<Result: ExportSurfaceResult>: Decodable, Equatable, Sendable {
    let schemaVersion: String
    let operation: ExportOperation
    let status: ExportResponseStatus
    let result: Result?
    let error: ExportSurfaceError?

    init(from decoder: Decoder) throws {
        try decoder.requireExactExportKeys(
            ["error", "operation", "result", "schema_version", "status"],
            model: "export response"
        )
        let container = try decoder.container(keyedBy: CodingKeys.self)
        schemaVersion = try container.decode(String.self, forKey: .schemaVersion)
        operation = try container.decode(ExportOperation.self, forKey: .operation)
        status = try container.decode(ExportResponseStatus.self, forKey: .status)
        result = try container.decodeIfPresent(Result.self, forKey: .result)
        error = try container.decodeIfPresent(ExportSurfaceError.self, forKey: .error)

        try requireExportSchema(
            schemaVersion,
            expected: ExportSurfaceSchema.response,
            model: "export response"
        )
        guard operation == Result.operation else {
            throw ExportSurfaceModelError.invalidValue(
                "Export response operation does not match its requested result type."
            )
        }
        switch status {
        case .ok:
            guard result != nil, error == nil else {
                throw ExportSurfaceModelError.invalidValue("Successful export response is incomplete.")
            }
        case .error, .cancelled:
            guard result == nil, error != nil else {
                throw ExportSurfaceModelError.invalidValue("Failed export response has inconsistent evidence.")
            }
        case .visiblePartial:
            guard operation == .execute, result != nil, error != nil else {
                throw ExportSurfaceModelError.invalidValue("Visible partial response must bind execute evidence and an error.")
            }
        }
    }

    enum CodingKeys: String, CodingKey {
        case schemaVersion = "schema_version"
        case operation
        case status
        case result
        case error
    }
}

private enum ExportSelectedRequestV2CodingKeys: String, CodingKey {
    case schemaVersion = "schema_version"
    case operation
    case bundle
    case containerID = "container_id"
    case containerVersion = "container_version"
    case consumerID = "consumer_id"
    case consumerProfileVersion = "consumer_profile_version"
    case sourceTrustPolicy = "source_trust_policy"
    case expectedManifestSHA256 = "expected_manifest_sha256"
    case overwritePolicy = "overwrite_policy"
    case containerOptions = "container_options"
    case destinationRoot = "destination_root"
    case expectedExportPlanID = "expected_export_plan_id"
}

private func encodeSelectedExportRequestV2(
    to encoder: Encoder,
    operation: ExportOperation,
    bundle: String,
    containerID: String,
    containerVersion: Int,
    consumerID: String?,
    consumerProfileVersion: Int?,
    sourceTrustPolicy: ExportSourceTrustPolicy,
    expectedManifestSHA256: String?,
    containerOptions: SplitJSONLOptions,
    destinationRoot: String? = nil,
    expectedExportPlanID: String? = nil
) throws {
    guard (destinationRoot == nil) == (expectedExportPlanID == nil) else {
        throw ExportSurfaceModelError.invalidValue(
            "Configured export destination and expected plan must be supplied together."
        )
    }
    var container = encoder.container(keyedBy: ExportSelectedRequestV2CodingKeys.self)
    try container.encode(ExportSurfaceSchema.requestV2, forKey: .schemaVersion)
    try container.encode(operation, forKey: .operation)
    try container.encode(bundle, forKey: .bundle)
    try container.encode(containerID, forKey: .containerID)
    try container.encode(containerVersion, forKey: .containerVersion)
    if let consumerID {
        try container.encode(consumerID, forKey: .consumerID)
    } else {
        try container.encodeNil(forKey: .consumerID)
    }
    if let consumerProfileVersion {
        try container.encode(consumerProfileVersion, forKey: .consumerProfileVersion)
    } else {
        try container.encodeNil(forKey: .consumerProfileVersion)
    }
    try container.encode(sourceTrustPolicy, forKey: .sourceTrustPolicy)
    if let expectedManifestSHA256 {
        try container.encode(expectedManifestSHA256, forKey: .expectedManifestSHA256)
    } else {
        try container.encodeNil(forKey: .expectedManifestSHA256)
    }
    try container.encode(ExportOverwritePolicy.refuse, forKey: .overwritePolicy)
    try container.encode(containerOptions, forKey: .containerOptions)
    if let destinationRoot, let expectedExportPlanID {
        try container.encode(destinationRoot, forKey: .destinationRoot)
        try container.encode(expectedExportPlanID, forKey: .expectedExportPlanID)
    }
}

private struct ExportDynamicCodingKey: CodingKey {
    let stringValue: String
    let intValue: Int? = nil

    init?(stringValue: String) {
        self.stringValue = stringValue
    }

    init?(intValue: Int) {
        return nil
    }
}

private extension Decoder {
    func requireExactExportKeys(_ expected: Set<String>, model: String) throws {
        let container = try self.container(keyedBy: ExportDynamicCodingKey.self)
        let observed = Set(container.allKeys.map(\.stringValue))
        guard observed == expected else {
            throw ExportSurfaceModelError.invalidKeySet(
                model: model,
                missing: Array(expected.subtracting(observed)).sorted(),
                unexpected: Array(observed.subtracting(expected)).sorted()
            )
        }
    }
}

private func validateExportSelection(
    bundle: String,
    containerID: String,
    containerVersion: Int,
    consumerID: String?,
    consumerProfileVersion: Int?,
    sourceTrustPolicy: ExportSourceTrustPolicy,
    expectedManifestSHA256: String?
) throws {
    try validateExportRuntimePath(bundle, label: "bundle")
    try validateExportSelector(containerID, label: "container_id")
    guard containerVersion > 0 else {
        throw ExportSurfaceModelError.invalidValue("container_version must be positive.")
    }
    guard (consumerID == nil) == (consumerProfileVersion == nil) else {
        throw ExportSurfaceModelError.invalidValue(
            "consumer_id and consumer_profile_version must be supplied together."
        )
    }
    if let consumerID {
        try validateExportSelector(consumerID, label: "consumer_id")
    }
    if let consumerProfileVersion, consumerProfileVersion < 1 {
        throw ExportSurfaceModelError.invalidValue("consumer_profile_version must be positive.")
    }
    if let expectedManifestSHA256 {
        try validateExportSHA256(expectedManifestSHA256, label: "expected_manifest_sha256")
    }
    if sourceTrustPolicy == .requireExternalDigest, expectedManifestSHA256 == nil {
        throw ExportSurfaceModelError.invalidValue(
            "require_external_digest needs expected_manifest_sha256."
        )
    }
}

private func validateConfiguredSplitJSONLSelection(
    bundle: String,
    containerID: String,
    containerVersion: Int,
    consumerID: String?,
    consumerProfileVersion: Int?,
    sourceTrustPolicy: ExportSourceTrustPolicy,
    expectedManifestSHA256: String?
) throws {
    try validateExportSelection(
        bundle: bundle,
        containerID: containerID,
        containerVersion: containerVersion,
        consumerID: consumerID,
        consumerProfileVersion: consumerProfileVersion,
        sourceTrustPolicy: sourceTrustPolicy,
        expectedManifestSHA256: expectedManifestSHA256
    )
    guard containerID == "split-jsonl-directory",
          containerVersion == 1,
          consumerID == nil,
          consumerProfileVersion == nil
    else {
        throw ExportSurfaceModelError.invalidValue(
            "split-jsonl-options/v1 requires split-jsonl-directory v1 without a consumer profile."
        )
    }
}

private func validateSplitJSONLPartitionName(_ value: String, label: String) throws {
    let allowed = CharacterSet(charactersIn: "abcdefghijklmnopqrstuvwxyz0123456789_-")
    let firstAllowed = CharacterSet(charactersIn: "abcdefghijklmnopqrstuvwxyz0123456789")
    let reserved = Set(
        ["con", "prn", "aux", "nul"]
            + (1 ... 9).flatMap { ["com\($0)", "lpt\($0)"] }
    )
    guard !value.isEmpty,
          value.utf8.count <= 64,
          value.unicodeScalars.allSatisfy(allowed.contains),
          value.unicodeScalars.first.map(firstAllowed.contains) == true,
          !reserved.contains(value)
    else {
        throw ExportSurfaceModelError.invalidValue(
            "\(label) must be a portable 1-64 character lowercase ASCII partition stem."
        )
    }
}

private func validateExportRuntimePath(_ value: String, label: String) throws {
    guard !value.isEmpty,
          !value.contains("\0"),
          value.utf8.count <= 32 * 1024
    else {
        throw ExportSurfaceModelError.invalidValue(
            "\(label) must be a non-empty exact path string of at most 32 KiB UTF-8."
        )
    }
}

private func validateExportSelector(_ value: String, label: String) throws {
    let allowed = CharacterSet(charactersIn: "abcdefghijklmnopqrstuvwxyz0123456789._-")
    let firstAllowed = CharacterSet(charactersIn: "abcdefghijklmnopqrstuvwxyz0123456789")
    guard !value.isEmpty,
          value.unicodeScalars.allSatisfy(allowed.contains),
          value.unicodeScalars.first.map(firstAllowed.contains) == true
    else {
        throw ExportSurfaceModelError.invalidValue("\(label) must be a lowercase canonical identifier.")
    }
}

private func validateExportSHA256(_ value: String, label: String) throws {
    let allowed = CharacterSet(charactersIn: "0123456789abcdef")
    guard value.utf8.count == 64, value.unicodeScalars.allSatisfy(allowed.contains) else {
        throw ExportSurfaceModelError.invalidValue("\(label) must be lowercase SHA-256.")
    }
}

private func validateExportID(_ value: String, kind: String) throws {
    let expression = "^\(NSRegularExpression.escapedPattern(for: kind))-v[1-9][0-9]*-[0-9a-f]{64}$"
    guard value.range(of: expression, options: .regularExpression) != nil else {
        throw ExportSurfaceModelError.invalidValue("Expected a valid \(kind) identifier.")
    }
}

private func requireExportSchema(
    _ observed: String,
    expected: String,
    model: String
) throws {
    guard observed == expected else {
        throw ExportSurfaceModelError.invalidValue("\(model) schema is unsupported: \(observed).")
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
