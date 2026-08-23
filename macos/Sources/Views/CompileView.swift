import SwiftUI

struct CompileView: View {
    @EnvironmentObject private var workbench: WorkbenchViewModel
    @State private var showAdvanced = false
    @State private var showRecipeSettings = false
    @State private var showIntegrations = false
    @State private var showTaxonomy = false
    @State private var showPreflightDetails = false

    var body: some View {
        HSplitView {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    Text("Compile")
                        .font(.title2.weight(.semibold))
                    Text("Turn sources into a sealed training dataset (.vfbundle).")
                        .foregroundStyle(.secondary)

                    SourceDropView()

                    Text("Start with one file if you are learning the flow. Multiple sources are supported.")
                        .font(.caption)
                        .foregroundStyle(.secondary)

                    configurationPanel

                    preflightPanel

                    if let reason = workbench.compileBlockedReason, !workbench.isRunning {
                        Text(reason)
                            .font(.caption)
                            .foregroundStyle(.orange)
                    }

                    HStack {
                        Button {
                            workbench.compile()
                        } label: {
                            Label(
                                workbench.isRunning ? "Compiling…" : "Compile to sealed bundle",
                                systemImage: "shippingbox.fill"
                            )
                            .frame(maxWidth: .infinity)
                        }
                        .buttonStyle(.borderedProminent)
                        .controlSize(.large)
                        .disabled(!workbench.canCompile)

                        if !workbench.runHistory.isEmpty {
                            Button("Re-run last") {
                                workbench.reRunLastConfiguration()
                            }
                            .disabled(workbench.isRunning)
                        }
                    }

                    if let result = workbench.lastResult {
                        ResultView(result: result)
                    }
                }
                .padding(20)
                .frame(minWidth: 360)
            }

            VStack(spacing: 0) {
                StagePanelView()
                    .padding()
                Divider()
                LogView()
            }
            .frame(minWidth: 320)
        }
    }

    private var configurationPanel: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Configuration")
                .font(.headline)

            goalSelection

            DisclosureGroup("Dataset taxonomy", isExpanded: $showTaxonomy) {
                taxonomyHelpContent
                    .padding(.top, 4)
            }

            DisclosureGroup("Recipe settings", isExpanded: $showRecipeSettings) {
                advancedEditor
                    .padding(.top, 4)
            }

            HStack {
                Button("Output folder…") { workbench.chooseOutputDirectory() }
                if let out = workbench.outputDirectoryURL {
                    Text(out.path)
                        .lineLimit(1)
                        .truncationMode(.middle)
                        .foregroundStyle(.secondary)
                        .help(out.path)
                }
            }

            DisclosureGroup("Integrations (optional)", isExpanded: $showIntegrations) {
                VStack(alignment: .leading, spacing: 6) {
                    Toggle("Write Aptus handoff file", isOn: $workbench.writeAptusHandoff)
                    Text("Off by default. Writes a sibling compatibility descriptor; Veriformis compilation and verification do not require it.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                }
                .padding(.top, 4)
            }

            DisclosureGroup("Advanced", isExpanded: $showAdvanced) {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Source root must be a directory that contains the source files.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    HStack {
                        Button("Source root…") { workbench.chooseSourceRoot() }
                        if let root = workbench.resolvedSourceRoot {
                            Text(root.path)
                                .lineLimit(1)
                                .truncationMode(.middle)
                                .foregroundStyle(.secondary)
                                .help(root.path)
                        }
                    }
                }
                .padding(.top, 4)
            }
        }
    }

    private var preflightPanel: some View {
        GroupBox {
            VStack(alignment: .leading, spacing: 10) {
                switch workbench.compilePreflightState {
                case .idle:
                    Text("Check source eligibility, goal evidence, expected exclusions, and known limitations before compiling.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                    Button("Check sources and recipe") {
                        workbench.refreshCompilePreflight()
                    }
                    .disabled(!workbench.canPreflight)

                case .loading:
                    HStack(spacing: 8) {
                        ProgressView()
                            .controlSize(.small)
                        Text("Checking the current source snapshot…")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                        Spacer()
                        Button("Cancel") {
                            if workbench.isRunning {
                                workbench.cancelCompile()
                            } else {
                                workbench.cancelCompilePreflight()
                            }
                        }
                        .controlSize(.small)
                    }

                case .unavailable(let message):
                    Label("Preflight unavailable", systemImage: "exclamationmark.triangle.fill")
                        .foregroundStyle(.orange)
                    Text(message)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .textSelection(.enabled)
                        .fixedSize(horizontal: false, vertical: true)
                    Button("Retry") { workbench.refreshCompilePreflight() }
                        .disabled(!workbench.canPreflight)

                case .ready(let report):
                    HStack(alignment: .firstTextBaseline) {
                        Label(
                            report.admitted ? "Ready to compile" : "Preflight found blockers",
                            systemImage: report.admitted
                                ? "checkmark.circle.fill"
                                : "xmark.octagon.fill"
                        )
                        .foregroundStyle(report.admitted ? .green : .red)
                        Spacer()
                        Button("Check again") { workbench.refreshCompilePreflight() }
                            .controlSize(.small)
                            .disabled(!workbench.canPreflight)
                    }
                    Text(
                        "\(report.counts.admittedSourceCount) of \(report.counts.sourceCount) sources admitted · evaluated through \(report.evaluatedThrough.rawValue)"
                    )
                    .font(.caption.monospaced())
                    .foregroundStyle(.secondary)

                    if !report.incompatibilities.isEmpty {
                        preflightMessages(
                            report.incompatibilities.map {
                                "[\($0.code.rawValue)] \($0.message)"
                            }
                        )
                    }
                    if !report.coverageBlockers.isEmpty {
                        preflightMessages(
                            report.coverageBlockers.map {
                                "[\($0.blockerCodes.joined(separator: ", "))] source \($0.sourceID)"
                            }
                        )
                    }

                    DisclosureGroup("Report details", isExpanded: $showPreflightDetails) {
                        VStack(alignment: .leading, spacing: 8) {
                            ForEach(Array(report.sources.enumerated()), id: \.offset) { _, source in
                                VStack(alignment: .leading, spacing: 2) {
                                    Label(
                                        source.logicalPath,
                                        systemImage: source.admitted
                                            ? "checkmark.circle"
                                            : "xmark.circle"
                                    )
                                    .font(.caption.weight(.semibold))
                                    Text(
                                        "\(source.inputFamily ?? "unclassified") · \(source.parserID ?? "no parser") · \(source.parserStatus.rawValue)"
                                    )
                                    .font(.caption.monospaced())
                                    .foregroundStyle(.secondary)
                                    ForEach(Array(source.refusalReasons.enumerated()), id: \.offset) { _, refusal in
                                        Text("[\(refusal.code.rawValue)] \(refusal.message)")
                                            .font(.caption)
                                            .foregroundStyle(.red)
                                            .fixedSize(horizontal: false, vertical: true)
                                    }
                                }
                            }

                            if !report.missingEvidence.isEmpty {
                                Text("Missing evidence")
                                    .font(.caption.weight(.semibold))
                                preflightMessages(
                                    report.missingEvidence.map { "[\($0.code)] \($0.message)" }
                                )
                            }

                            if !report.expectedExclusionCounts.isEmpty {
                                Text("Expected exclusions")
                                    .font(.caption.weight(.semibold))
                                preflightMessages(
                                    report.expectedExclusionCounts.map {
                                        "\($0.stage.rawValue) · \($0.status.rawValue) · [\($0.reasonCode)] \($0.count)"
                                    }
                                )
                            }

                            ForEach(Array(report.expectedExclusions.enumerated()), id: \.offset) { _, exclusion in
                                Text(
                                    "\(exclusion.subjectID): \(exclusion.reasonCodes.joined(separator: ", "))"
                                )
                                .font(.caption.monospaced())
                                .foregroundStyle(.secondary)
                                .textSelection(.enabled)
                            }

                            if !report.knownLimitations.isEmpty {
                                Text("Known limitations")
                                    .font(.caption.weight(.semibold))
                                preflightMessages(
                                    report.knownLimitations.map { "[\($0.code)] \($0.message)" }
                                )
                            }

                            if report.omittedDiagnosticCount > 0
                                || report.omittedExpectedExclusionCount > 0
                            {
                                Text(
                                    "Omitted details: \(report.omittedDiagnosticCount) diagnostics, \(report.omittedExpectedExclusionCount) expected exclusions."
                                )
                                .font(.caption)
                                .foregroundStyle(.secondary)
                            }

                            Text("Request \(report.requestDigest)")
                                .font(.caption2.monospaced())
                                .foregroundStyle(.secondary)
                                .textSelection(.enabled)
                        }
                        .padding(.top, 4)
                    }
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        } label: {
            Label("Compile preflight", systemImage: "checklist.checked")
                .font(.headline)
        }
    }

    private func preflightMessages(_ messages: [String]) -> some View {
        VStack(alignment: .leading, spacing: 3) {
            ForEach(Array(messages.enumerated()), id: \.offset) { _, message in
                Text(message)
                    .font(.caption)
                    .fixedSize(horizontal: false, vertical: true)
                    .textSelection(.enabled)
            }
        }
    }

    @ViewBuilder
    private var taxonomyHelpContent: some View {
        switch workbench.taxonomyHelpState {
        case .idle:
            HStack(spacing: 8) {
                Text("Taxonomy has not been loaded.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Button("Load") { workbench.refreshTaxonomyHelp() }
                    .controlSize(.small)
            }
        case .loading:
            HStack(spacing: 8) {
                ProgressView()
                    .controlSize(.small)
                Text("Loading taxonomy from Veriformis…")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        case .ready(let discovery):
            VStack(alignment: .leading, spacing: 6) {
                Text(discovery.schemaID)
                    .font(.caption.monospaced())
                    .foregroundStyle(.secondary)
                    .textSelection(.enabled)
                taxonomyAxis("Training families", values: discovery.trainingFamilies)
                taxonomyAxis("Objectives", values: discovery.objectives)
                taxonomyAxis("Semantic rows", values: discovery.semanticRows)
                taxonomyAxis("Physical containers", values: discovery.physicalContainers)
                taxonomyAxis("Consumer profiles", values: discovery.consumerProfiles)
                taxonomyAxis("Loss policies", values: discovery.lossPolicies)
                taxonomyAxis("Input families", values: discovery.inputFamilies)
            }
        case .unavailable(let message):
            VStack(alignment: .leading, spacing: 6) {
                Text("Taxonomy unavailable")
                    .font(.caption.weight(.semibold))
                Text(message)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
                Button("Retry") { workbench.refreshTaxonomyHelp() }
                    .controlSize(.small)
            }
        }
    }

    /// Plain-language goal and preset selection driven by `veriformis goals`
    /// and `veriformis presets`; the workbench holds no recipe constants.
    @ViewBuilder
    private var goalSelection: some View {
        switch (workbench.goalCatalogState, workbench.recipePresetState) {
        case (.ready(let goals), .ready(let presets)):
            VStack(alignment: .leading, spacing: 6) {
                Picker(
                    "What should the model learn?",
                    selection: Binding(
                        get: { workbench.selectedGoalID ?? goals.goals.first?.goalID ?? "" },
                        set: { workbench.selectGoal($0) }
                    )
                ) {
                    ForEach(goals.goals, id: \.goalID) { goal in
                        Text(goal.title).tag(goal.goalID)
                    }
                }
                if let goal = workbench.selectedGoal {
                    Text(goal.plainLanguage)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                    Text(goal.whatTheModelLearns)
                        .font(.caption)
                        .fixedSize(horizontal: false, vertical: true)
                    GoalDisclosuresView(
                        notThis: goal.notThis,
                        nonClaims: goal.nonClaims
                    )
                    let options = presets.presets(forGoal: goal.goalID)
                    Picker(
                        "Preset",
                        selection: Binding(
                            get: { workbench.selectedPresetID ?? options.first?.presetID ?? "" },
                            set: { workbench.selectedPresetID = $0 }
                        )
                    ) {
                        ForEach(options, id: \.presetID) { preset in
                            Text(preset.title).tag(preset.presetID)
                        }
                    }
                    if let preset = workbench.selectedPreset {
                        Text(preset.plainLanguage)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }
            }
        case (.unavailable(let message), _), (_, .unavailable(let message)):
            Text(message)
                .font(.caption)
                .foregroundStyle(.secondary)
                .textSelection(.enabled)
        default:
            ProgressView("Loading goals and presets…")
        }
    }

    /// Explicit operator overrides on top of the selected preset.
    @ViewBuilder
    private var advancedEditor: some View {
        VStack(alignment: .leading, spacing: 8) {
            if let preset = workbench.selectedPreset {
                if workbench.selectedGoal?.objective == .continuation {
                    HStack {
                        Text("Opening share (ppm)")
                        TextField(
                            String(preset.construction.splitRatioPPM),
                            value: $workbench.splitRatioPPM,
                            format: .number
                        )
                        .textFieldStyle(.roundedBorder)
                        .frame(width: 110)
                    }
                    Text("Leave empty to use the preset value \(preset.construction.splitRatioPPM) ppm of the passage as the opening.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                }
                Toggle("Allow empty evaluation partition", isOn: $workbench.allowEmptyEvaluation)
                Text("Off by default: the preset requires an evaluation partition (\(preset.curation.evaluationRatioPPM) ppm held out), so compiles fail closed when it would be empty. Enable only when a single leakage group leaves evaluation empty.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
                Text("Segmentation \(preset.segmentation.strategy) · size \(preset.segmentation.size) · overlap \(preset.segmentation.overlap) · minimum target \(preset.curation.minimumTargetCharacters) · seed \(preset.curation.splitSeed)")
                    .font(.caption.monospaced())
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            } else {
                Text("Advanced settings appear once presets are loaded.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
    }

    private func taxonomyAxis(_ title: String, values: [String]) -> some View {
        VStack(alignment: .leading, spacing: 1) {
            Text(title)
                .font(.caption.weight(.semibold))
            Text(values.joined(separator: ", "))
                .font(.caption.monospaced())
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
                .textSelection(.enabled)
        }
    }
}

/// One pure presentation of goal exclusions and contract non-claims, reused
/// wherever the workbench shows a goal so picker and preview cannot drift.
struct GoalDisclosuresView: View {
    let lines: [GoalDisclosureLine]

    init(notThis: [String], nonClaims: [String]) {
        lines = GoalDisclosureLine.disclosures(
            notThis: notThis,
            nonClaims: nonClaims
        )
    }

    var body: some View {
        ForEach(lines) { line in
            Text(line.renderedText)
                .font(line.kind == .nonClaim ? .caption.monospaced() : .caption)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
        }
    }
}
