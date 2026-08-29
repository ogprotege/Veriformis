import SwiftUI

struct ReviewView: View {
    @EnvironmentObject private var workbench: WorkbenchViewModel

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text("Review")
                    .font(.title2.weight(.semibold))
                Text("Wrap existing review-export, review-import, and review-submit packets. Default review_policy stays none. Required unresolved reviews still block seal. Corrections bind a new transform or mapping-plan identity. This panel does not invent a review policy.")
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)

                exportPanel
                importSubmitPanel
                cliEquivalentPanel
            }
            .padding(24)
            .frame(maxWidth: 820, alignment: .leading)
        }
    }

    private var exportPanel: some View {
        GroupBox("Export a pending packet") {
            VStack(alignment: .leading, spacing: 10) {
                Text("Finished-dataset plan_id")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                TextField("fdp-v1-…", text: $workbench.reviewPlanID)
                    .textFieldStyle(.roundedBorder)
                    .accessibilityLabel("Finished dataset plan identity")
                Text(workbench.reviewItemsURL?.path ?? "Choose items JSON")
                    .font(.system(.body, design: .monospaced))
                    .textSelection(.enabled)
                Button("Choose items…") { workbench.chooseReviewItems() }
                    .accessibilityLabel("Choose review items JSON file")
                Button("Export packet") { workbench.exportReviewPacket() }
                    .accessibilityLabel("Export pending review packet")
                    .disabled(!workbench.canExportReviewPacket)
                switch workbench.reviewExportState {
                case .idle:
                    Text("Export writes a pending packet. Decisions stay vacant.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                case .loading:
                    ProgressView("Exporting review packet…")
                case .unavailable(let message):
                    Text(message)
                        .foregroundStyle(.orange)
                        .textSelection(.enabled)
                case .ready(let packet):
                    packetSummary(packet)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.vertical, 4)
        }
    }

    private var importSubmitPanel: some View {
        GroupBox("Import and submit") {
            VStack(alignment: .leading, spacing: 10) {
                Text(workbench.reviewPacketURL?.path ?? "Choose packet JSON")
                    .font(.system(.body, design: .monospaced))
                    .textSelection(.enabled)
                Button("Choose packet…") { workbench.chooseReviewPacket() }
                    .accessibilityLabel("Choose review packet JSON file")
                Button("Import packet") { workbench.importReviewPacket() }
                    .accessibilityLabel("Import review packet without submitting")
                    .disabled(!workbench.canImportReviewPacket)
                switch workbench.reviewImportState {
                case .idle:
                    Text("Import validates the packet without submitting it.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                case .loading:
                    ProgressView("Importing review packet…")
                case .unavailable(let message):
                    Text(message)
                        .foregroundStyle(.orange)
                        .textSelection(.enabled)
                case .ready(let packet):
                    packetSummary(packet)
                }
                Toggle("I confirm this packet for submit", isOn: $workbench.reviewSubmitConfirmed)
                    .accessibilityLabel("Confirm review packet for submit")
                    .disabled(!workbench.canImportReviewPacket)
                Button("Submit review") { workbench.submitConfirmedReview() }
                    .accessibilityLabel("Submit confirmed review packet")
                    .disabled(!workbench.canSubmitReviewPacket)
                switch workbench.reviewSubmitState {
                case .idle:
                    EmptyView()
                case .loading:
                    ProgressView("Submitting review…")
                case .unavailable(let message):
                    Text(message)
                        .foregroundStyle(.orange)
                        .textSelection(.enabled)
                case .ready(let bundle):
                    bundleSummary(bundle)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.vertical, 4)
        }
    }

    private var cliEquivalentPanel: some View {
        GroupBox("CLI equivalent") {
            VStack(alignment: .leading, spacing: 8) {
                if let equivalent = workbench.currentReviewCLIEquivalent {
                    Text(equivalent)
                        .font(.system(.caption, design: .monospaced))
                        .textSelection(.enabled)
                    Button("Copy CLI equivalent") {
                        workbench.copyToPasteboard(equivalent, label: "review CLI equivalent")
                    }
                    .accessibilityLabel("Copy review CLI equivalent")
                } else {
                    Text("Choose a plan_id, items file, or packet file to project the CLI.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.vertical, 4)
        }
    }

    private func packetSummary(_ packet: ReviewPacketSummary) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            labeled("Packet id", packet.packetID)
            labeled("Plan id", packet.planID)
            labeled("Items", String(packet.items.count))
            labeled("Decisions", String(packet.decisions.count))
            labeled("Waivers", String(packet.waivers.count))
            labeled("Corrections", String(packet.corrections.count))
            ForEach(packet.corrections, id: \.correctionID) { correction in
                Text("Correction \(correction.kind) → \(correction.resultID)")
                    .font(.caption.monospaced())
                    .textSelection(.enabled)
            }
            Text("Corrections are new identities. They do not mutate accepted records in place.")
                .font(.caption)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private func bundleSummary(_ bundle: ReviewBundleSummary) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            labeled("Bundle id", bundle.bundleID)
            labeled("Plan id", bundle.planID)
            labeled("Blocks seal", bundle.blocksSeal ? "true" : "false")
            labeled("Queues", bundle.queues.joined(separator: ", "))
            labeled("Limitations", bundle.limitations.joined(separator: ", "))
            ForEach(bundle.corrections, id: \.correctionID) { correction in
                Text("Correction \(correction.kind) → \(correction.resultID)")
                    .font(.caption.monospaced())
                    .textSelection(.enabled)
            }
            Text("Required unresolved reviews still block seal. Default recipes stay none.")
                .font(.caption)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private func labeled(_ title: String, _ value: String) -> some View {
        HStack(alignment: .top) {
            Text(title)
                .foregroundStyle(.secondary)
                .frame(width: 120, alignment: .leading)
            Text(value)
                .textSelection(.enabled)
                .font(.system(.body, design: .monospaced))
        }
    }
}
