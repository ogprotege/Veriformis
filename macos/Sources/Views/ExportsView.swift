import AppKit
import SwiftUI

struct ExportsView: View {
    @EnvironmentObject private var workbench: WorkbenchViewModel

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text("Exports")
                    .font(.title2.weight(.semibold))
                Text("Export a sealed, independently verified .vfbundle through the existing CLI. Generic containers come first. Named profiles appear only for schemas they admit. Execute waits for an operator-confirmed dry-run plan. This panel does not train, mutate membership, or upload to a Hub.")
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)

                identityPanel
                selectionPanel
                cliEquivalentPanel
                dryRunPanel
                executePanel
                inspectAndVerifyPanel

                if let reason = workbench.exportBlockedReason, !workbench.exportIsRunning {
                    Text(reason)
                        .font(.caption)
                        .foregroundStyle(.orange)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
            .padding(24)
            .frame(maxWidth: 820, alignment: .leading)
        }
        .onAppear {
            workbench.adoptExportBundleIfNeeded()
            if case .idle = workbench.exportDiscoveryState {
                workbench.discoverExports()
            }
        }
    }

    private var identityPanel: some View {
        GroupBox("Source bundle and receipt") {
            VStack(alignment: .leading, spacing: 8) {
                gridRow("Bundle", workbench.resolvedExportBundleURL?.path ?? "(none)")
                if let sha = workbench.resolvedExportManifestSHA256 {
                    digestRow("Manifest SHA-256", sha, copyLabel: "manifest SHA-256")
                }
                if let plan = workbench.exportPlanSummary {
                    gridRow("Source bundle id", plan.sourceBundleID)
                    digestRow(
                        "Source manifest SHA-256",
                        plan.sourceManifestSHA256,
                        copyLabel: "source manifest SHA-256"
                    )
                    gridRow("Export plan id", plan.exportPlanID)
                    gridRow("Row schema", plan.rowSchema)
                    gridRow("Trust grade", plan.sourceTrustGrade.rawValue)
                    gridRow("Overwrite policy", plan.overwritePolicy.rawValue)
                }
                if let receipt = workbench.exportReceiptSummary {
                    digestRow(
                        "Export receipt id",
                        receipt.exportReceiptID,
                        copyLabel: "export receipt id"
                    )
                    digestRow(
                        "Receipt SHA-256",
                        receipt.canonicalSHA256,
                        copyLabel: "export receipt SHA-256"
                    )
                    digestRow(
                        "Output content root SHA-256",
                        receipt.outputContentRootSHA256,
                        copyLabel: "output content root SHA-256"
                    )
                }
                Text("Bundle identity and receipt stay visible. Membership is not rewritten here.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.vertical, 4)
        }
    }

    private var selectionPanel: some View {
        GroupBox("Container and destination") {
            VStack(alignment: .leading, spacing: 10) {
                Text(workbench.resolvedExportBundleURL?.path ?? "Choose a sealed .vfbundle")
                    .font(.system(.body, design: .monospaced))
                    .textSelection(.enabled)
                HStack {
                    Button("Choose bundle…") { workbench.chooseExportBundle() }
                        .accessibilityLabel("Choose sealed bundle for export")
                    Button("Use last compile") { workbench.adoptExportBundleIfNeeded(force: true) }
                        .accessibilityLabel("Use last compiled bundle for export")
                        .disabled(workbench.lastResult == nil)
                    Button("Refresh discovery") { workbench.discoverExports() }
                        .accessibilityLabel("Refresh export discovery")
                }

                Picker("Source trust policy", selection: $workbench.exportSourceTrustPolicy) {
                    Text("allow_self_consistent").tag(ExportSourceTrustPolicy.allowSelfConsistent)
                    Text("require_external_digest").tag(ExportSourceTrustPolicy.requireExternalDigest)
                }
                .accessibilityLabel("Export source trust policy")
                Text("Local seal grades are usually self_consistent. require_external_digest needs an out-of-band manifest digest.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)

                switch workbench.exportDiscoveryState {
                case .idle:
                    Text("Discovery has not run.")
                        .foregroundStyle(.secondary)
                case .loading:
                    ProgressView("Discovering export implementations…")
                case .unavailable(let message):
                    Text(message)
                        .foregroundStyle(.secondary)
                        .textSelection(.enabled)
                case .ready:
                    Picker("Profile", selection: $workbench.selectedExportProfileKey) {
                        Text("(select)").tag("")
                        if !workbench.genericExportProfiles.isEmpty {
                            Section("Generic containers") {
                                ForEach(workbench.genericExportProfiles, id: \.selectionKey) { profile in
                                    Text(profile.displayName).tag(profile.selectionKey)
                                }
                            }
                        }
                        if !workbench.namedExportProfiles.isEmpty {
                            Section("Named profiles admitted for this schema") {
                                ForEach(workbench.namedExportProfiles, id: \.selectionKey) { profile in
                                    Text(profile.displayName).tag(profile.selectionKey)
                                }
                            }
                        }
                    }
                    .accessibilityLabel("Export container or named profile")
                    if workbench.knownExportRowSchema == nil {
                        Text("Named profiles wait until a row schema is known from the selected goal or a dry-run.")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .fixedSize(horizontal: false, vertical: true)
                    } else if workbench.namedExportProfiles.isEmpty {
                        Text("No named profile admits schema \(workbench.knownExportRowSchema ?? ""). Family schemas stay on generic split-jsonl or json. Constrained CSV still refuses nested and family rows.")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }

                Text(workbench.resolvedExportDestinationURL?.path ?? "Choose an empty destination folder")
                    .font(.system(.body, design: .monospaced))
                    .textSelection(.enabled)
                Button("Choose destination…") { workbench.chooseExportDestination() }
                    .accessibilityLabel("Choose export destination folder")
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.vertical, 4)
        }
    }

    private var cliEquivalentPanel: some View {
        GroupBox("CLI equivalent") {
            VStack(alignment: .leading, spacing: 8) {
                if let equivalent = workbench.currentExportCLIEquivalent {
                    Text(equivalent)
                        .font(.system(.caption, design: .monospaced))
                        .textSelection(.enabled)
                    Button("Copy CLI equivalent") {
                        workbench.copyToPasteboard(equivalent, label: "export CLI equivalent")
                    }
                    .accessibilityLabel("Copy export CLI equivalent")
                } else {
                    Text("Choose a bundle, container, destination, and trust policy to project the CLI.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.vertical, 4)
        }
    }

    private var dryRunPanel: some View {
        GroupBox("Dry-run preview") {
            VStack(alignment: .leading, spacing: 8) {
                Button("Dry-run") { workbench.dryRunSelectedExport() }
                    .accessibilityLabel("Dry-run selected export")
                    .disabled(!workbench.canDryRunExport || workbench.exportIsRunning)
                switch workbench.exportDryRunState {
                case .idle:
                    Text("Dry-run does not write a destination.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                case .loading:
                    ProgressView("Running export dry-run…")
                case .unavailable(let message):
                    Text(message)
                        .foregroundStyle(.orange)
                        .textSelection(.enabled)
                case .ready(let result):
                    Text("Plan \(result.plan.exportPlanID)")
                        .font(.caption.monospaced())
                        .textSelection(.enabled)
                    Text("Destination tree")
                        .font(.caption.weight(.semibold))
                    ForEach(result.preview.destinationTree.directories, id: \.self) { path in
                        Text("dir  \(path)")
                            .font(.caption.monospaced())
                            .textSelection(.enabled)
                    }
                    ForEach(result.preview.destinationTree.files, id: \.self) { path in
                        Text("file \(path)")
                            .font(.caption.monospaced())
                            .textSelection(.enabled)
                    }
                    ForEach(result.preview.sampleRows, id: \.payloadSHA256) { sample in
                        Text("\(sample.partition.rawValue) sample · \(sample.payloadByteSize) bytes")
                            .font(.caption.monospaced())
                        if let reason = sample.omissionReason {
                            Text("Sample omitted: \(reason.rawValue)")
                                .font(.caption)
                                .foregroundStyle(.orange)
                        }
                    }
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.vertical, 4)
        }
    }

    private var executePanel: some View {
        GroupBox("Operator-confirmed execute") {
            VStack(alignment: .leading, spacing: 8) {
                Toggle("I confirm this dry-run plan", isOn: $workbench.exportPlanConfirmed)
                    .accessibilityLabel("Confirm export dry-run plan")
                    .disabled(!workbench.hasExportDryRunPlan || workbench.exportIsRunning)
                Text("Execute stays disabled until this confirmation. Overwrite remains refuse.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Button {
                    workbench.executeConfirmedExport()
                } label: {
                    Label(
                        workbench.exportIsRunning ? "Exporting…" : "Execute export",
                        systemImage: "square.and.arrow.up"
                    )
                }
                .accessibilityLabel("Execute confirmed export")
                .disabled(!workbench.canExecuteExport)
                switch workbench.exportExecuteState {
                case .idle:
                    EmptyView()
                case .loading:
                    ProgressView("Executing export…")
                case .unavailable(let message):
                    Text(message)
                        .foregroundStyle(.orange)
                        .textSelection(.enabled)
                case .ready(let result):
                    Text("Wrote \(result.destinationRoot)")
                        .font(.caption.monospaced())
                        .textSelection(.enabled)
                    if let warning = result.durabilityWarning {
                        Text(warning)
                            .font(.caption)
                            .foregroundStyle(.orange)
                    }
                case .visiblePartial(let result, let message):
                    Text("Visible partial: \(message)")
                        .foregroundStyle(.orange)
                    Text(result.destinationRoot)
                        .font(.caption.monospaced())
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.vertical, 4)
        }
    }

    private var inspectAndVerifyPanel: some View {
        GroupBox("Inspect and verify") {
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Button("Inspect destination") { workbench.inspectExportDestination() }
                        .accessibilityLabel("Inspect export destination")
                        .disabled(!workbench.canInspectExport || workbench.exportIsRunning)
                    Button("Verify export") { workbench.verifyExportDestination() }
                        .accessibilityLabel("Verify export against source bundle")
                        .disabled(!workbench.canVerifyExport || workbench.exportIsRunning)
                }
                if case .ready(let inspection) = workbench.exportInspectState {
                    Text("Inspected \(inspection.inspectionScope) · receipt \(inspection.receipt.exportReceiptID)")
                        .font(.caption.monospaced())
                        .textSelection(.enabled)
                }
                if case .unavailable(let message) = workbench.exportInspectState {
                    Text(message)
                        .foregroundStyle(.orange)
                }
                if case .ready(let verified) = workbench.exportVerifyState {
                    gridRow("Verification id", verified.verification.exportVerificationID)
                    gridRow("Source bundle id", verified.verification.sourceBundleID)
                    digestRow(
                        "Source manifest SHA-256",
                        verified.verification.sourceManifestSHA256,
                        copyLabel: "source manifest SHA-256"
                    )
                    digestRow(
                        "Export receipt id",
                        verified.verification.exportReceiptID,
                        copyLabel: "export receipt id"
                    )
                }
                if case .unavailable(let message) = workbench.exportVerifyState {
                    Text(message)
                        .foregroundStyle(.orange)
                }
                if let url = workbench.resolvedExportDestinationURL {
                    Button("Reveal destination") { workbench.reveal(url) }
                        .accessibilityLabel("Reveal export destination in Finder")
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.vertical, 4)
        }
    }

    private func gridRow(_ label: String, _ value: String) -> some View {
        HStack(alignment: .top) {
            Text(label)
                .foregroundStyle(.secondary)
                .frame(width: 180, alignment: .leading)
            Text(value)
                .textSelection(.enabled)
                .font(.system(.body, design: .monospaced))
        }
    }

    private func digestRow(_ label: String, _ value: String, copyLabel: String) -> some View {
        HStack(alignment: .top) {
            Text(label)
                .foregroundStyle(.secondary)
                .frame(width: 180, alignment: .leading)
            Text(value)
                .textSelection(.enabled)
                .font(.system(.body, design: .monospaced))
            Button("Copy") {
                workbench.copyToPasteboard(value, label: copyLabel)
            }
            .buttonStyle(.borderless)
            .accessibilityLabel("Copy \(copyLabel)")
        }
    }
}
