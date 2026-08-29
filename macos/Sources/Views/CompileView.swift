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
                    Text("Choose a compiler path (document-source, dataset-row, or mixed), add sources, choose a goal, and compile a sealed .vfbundle. Dataset-row requires a confirmed mapping plan. Aptus is optional Integrations, not required.")
                        .foregroundStyle(.secondary)
                        .fixedSize(horizontal: false, vertical: true)

                    SourceDropView()

                    Text("Start with one file if you are learning the flow. Multiple sources are supported.")
                        .font(.caption)
                        .foregroundStyle(.secondary)

                    configurationPanel

                    cliEquivalentPanel

                    if workbench.currentCompileUsesMapping {
                        mappingPanel
                    } else {
                        preflightPanel
                    }

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
            Text("Compiler path")
                .font(.headline)
            Picker("Compiler path", selection: $workbench.inputMode) {
                ForEach(CompilerInputMode.allCases) { mode in
                    Text(mode.rawValue).tag(mode)
                }
            }
            .pickerStyle(.segmented)
            .accessibilityLabel("Compiler path")
            Text(workbench.inputMode.subtitle)
                .font(.caption)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)

            Text("Goal")
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

    private var cliEquivalentPanel: some View {
        GroupBox {
            VStack(alignment: .leading, spacing: 8) {
                if let text = workbench.currentCompileCLIEquivalent {
                    Text(text)
                        .font(.system(.caption, design: .monospaced))
                        .textSelection(.enabled)
                        .fixedSize(horizontal: false, vertical: true)
                    Button("Copy CLI equivalent") {
                        workbench.copyToPasteboard(text, label: "CLI equivalent")
                    }
                    .controlSize(.small)
                    .accessibilityLabel("Copy CLI equivalent")
                } else {
                    Text("Choose sources, a compiler path, a goal, and an output folder to see the exact CLI equivalent of this compile plan. Dataset-row waits for a confirmed mapping plan.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        } label: {
            Label("CLI equivalent", systemImage: "terminal")
                .font(.headline)
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

    private var mappingPanel: some View {
        GroupBox {
            VStack(alignment: .leading, spacing: 10) {
                Text("Dataset-row mapping is confirm-then-map with mapped_value evidence. Detecting a plan does not confirm it.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)

                if workbench.mixedSourcesAreFused {
                    Text("mixed mode keeps construction and imported-row provenance distinct; compile document-source and dataset-row workspaces separately rather than fusing them in one stage graph")
                        .font(.caption)
                        .foregroundStyle(.red)
                        .fixedSize(horizontal: false, vertical: true)
                }

                Button("Detect mapping") {
                    workbench.detectMapping()
                }
                .disabled(!workbench.canDetectMapping)
                .accessibilityLabel("Detect mapping")

                switch workbench.mappingDetectState {
                case .idle:
                    Text("Run mapping-detect on the selected row-source file.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                case .loading:
                    HStack(spacing: 8) {
                        ProgressView()
                            .controlSize(.small)
                        Text("Detecting mapping plans…")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                case .unavailable(let message):
                    Text(message)
                        .font(.caption)
                        .foregroundStyle(.orange)
                        .fixedSize(horizontal: false, vertical: true)
                        .textSelection(.enabled)
                case .ready(let detected):
                    if let refusal = detected.refusal, detected.proposals.isEmpty {
                        Text(refusal)
                            .font(.caption)
                            .foregroundStyle(.red)
                            .fixedSize(horizontal: false, vertical: true)
                            .textSelection(.enabled)
                    } else {
                        Picker(
                            "Mapping proposal",
                            selection: Binding(
                                get: { workbench.selectedMappingProposalID ?? "" },
                                set: { workbench.selectedMappingProposalID = $0 }
                            )
                        ) {
                            ForEach(detected.proposals) { proposal in
                                Text(proposal.summary).tag(proposal.mappingPlanID)
                            }
                        }
                        .accessibilityLabel("Mapping proposal")
                        if let proposal = workbench.selectedMappingProposal {
                            Text(proposal.confirmationDigest)
                                .font(.caption2.monospaced())
                                .foregroundStyle(.secondary)
                                .textSelection(.enabled)
                            ForEach(proposal.fieldMappings, id: \.mappingRuleID) { field in
                                Text("\(field.sourcePath) → \(field.targetKey)")
                                    .font(.caption.monospaced())
                                    .textSelection(.enabled)
                            }
                        }
                        Button("Confirm mapping plan") {
                            workbench.confirmSelectedMappingPlan()
                        }
                        .disabled(workbench.selectedMappingProposal == nil || workbench.isRunning)
                        .accessibilityLabel("Confirm mapping plan")
                    }
                }

                if workbench.mappingIsConfirmed, let plan = workbench.confirmedMappingPlan {
                    Text("Confirmed \(plan.mappingPlanID)")
                        .font(.caption.monospaced())
                        .textSelection(.enabled)
                }

                switch workbench.mappingPreviewState {
                case .idle:
                    EmptyView()
                case .loading:
                    HStack(spacing: 8) {
                        ProgressView()
                            .controlSize(.small)
                        Text("Previewing confirmed mapping…")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                case .unavailable(let message):
                    Text(message)
                        .font(.caption)
                        .foregroundStyle(.orange)
                        .fixedSize(horizontal: false, vertical: true)
                        .textSelection(.enabled)
                case .ready(let preview):
                    Text(
                        "Preview \(preview.acceptedCount) accepted · \(preview.rejectedCount) rejected · \(preview.recordCount) records"
                    )
                    .font(.caption.monospaced())
                    .textSelection(.enabled)
                    if let omission = preview.omission {
                        Text("Omitted: \(omission)")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        } label: {
            Label("Mapping", systemImage: "arrow.left.arrow.right")
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
                    ForEach(workbench.selectableGoals, id: \.goalID) { goal in
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
                    ForEach(goal.notThis, id: \.self) { claim in
                        Text("Not this: \(claim)")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }
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

    /// Inspectable preset and goal contract. Defaults come from `veriformis presets`.
    @ViewBuilder
    private var advancedEditor: some View {
        VStack(alignment: .leading, spacing: 10) {
            if let preset = workbench.selectedPreset {
                Text("Values below are the selected versioned preset. Empty overrides keep that preset authoritative.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)

                inspectRow("Preset", preset.presetID)
                inspectRow("Representation", preset.representationID)
                if let representation = workbench.selectedRepresentation {
                    inspectRow("Row schema", representation.rowSchema)
                    inspectRow("Loss policy", representation.lossPolicy)
                    inspectRow(
                        "Compatible generic exports",
                        representation.compatibleGenericExports.joined(separator: ", ")
                    )
                }
                if let goal = workbench.selectedGoal {
                    inspectRow("Review policy (preset)", preset.reviewPolicy)
                    inspectRow("Review policy (goal default)", goal.reviewPolicyDefault)
                    inspectRow(
                        "Review policy options",
                        goal.reviewPolicyOptions.joined(separator: ", ")
                    )
                    inspectRow("Supervision boundary", goal.supervisionBoundary)
                    inspectRow("Non-claims", goal.nonClaims.joined(separator: ", "))
                }

                Text("Chunk")
                    .font(.caption.weight(.semibold))
                inspectRow("Strategy", preset.segmentation.strategy)
                inspectRow("Size", String(preset.segmentation.size))
                inspectRow("Overlap", String(preset.segmentation.overlap))

                Text("Construct")
                    .font(.caption.weight(.semibold))
                inspectRow("Split ratio (ppm)", String(preset.construction.splitRatioPPM))
                inspectRow("Require review", preset.construction.requireReview ? "true" : "false")
                inspectRow("Consumer profile", preset.construction.consumerProfile.isEmpty ? "(none)" : preset.construction.consumerProfile)
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
                        .accessibilityLabel("Opening share override in parts per million")
                    }
                    Text("Leave empty to use the preset value \(preset.construction.splitRatioPPM) ppm of the passage as the opening.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                }

                Text("Curate and split")
                    .font(.caption.weight(.semibold))
                inspectRow("Minimum target characters", String(preset.curation.minimumTargetCharacters))
                inspectRow("Balance mode", preset.curation.balanceMode)
                inspectRow("Evaluation ratio (ppm)", String(preset.curation.evaluationRatioPPM))
                inspectRow("Evaluation required", preset.curation.evaluationRequired ? "true" : "false")
                inspectRow("Split seed", preset.curation.splitSeed)
                Toggle("Allow empty evaluation partition", isOn: $workbench.allowEmptyEvaluation)
                    .accessibilityLabel("Allow empty evaluation partition")
                Text("Off by default: the preset requires an evaluation partition (\(preset.curation.evaluationRatioPPM) ppm held out), so compiles fail closed when it would be empty. Enable only when a single leakage group leaves evaluation empty.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)

                Text("Validation and profiles (inspect only)")
                    .font(.caption.weight(.semibold))
                Text("Finished-dataset validation stays the seal path. Named-profile export is on Exports and only for schemas the profile admits. This panel does not mutate membership.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
                inspectRow("Validation", "inspect-only; seal still runs validate")
                switch workbench.taxonomyHelpState {
                case .ready(let discovery):
                    inspectRow(
                        "Consumer profiles",
                        discovery.consumerProfiles.joined(separator: ", ")
                    )
                    inspectRow(
                        "Physical containers",
                        discovery.physicalContainers.joined(separator: ", ")
                    )
                default:
                    Text("Load Dataset taxonomy above to inspect consumer profiles and containers from CLI discovery.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                }
            } else {
                Text("Advanced settings appear once presets are loaded.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
    }

    private func inspectRow(_ title: String, _ value: String) -> some View {
        VStack(alignment: .leading, spacing: 1) {
            Text(title)
                .font(.caption.weight(.semibold))
            Text(value)
                .font(.caption.monospaced())
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
                .textSelection(.enabled)
                .accessibilityLabel("\(title): \(value)")
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
