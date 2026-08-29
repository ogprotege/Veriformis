import SwiftUI

struct HomeView: View {
    @EnvironmentObject private var workbench: WorkbenchViewModel

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                Text("Veriformis")
                    .font(.largeTitle.weight(.semibold))
                Text("Go from sources and a goal to a sealed, independently verified .vfbundle.")
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)

                GroupBox("Status") {
                    VStack(alignment: .leading, spacing: 8) {
                        labeled("CLI", workbench.resolvedCLIDescription)
                        labeled("Status", workbench.runStatusMessage)
                        if let last = workbench.runHistory.first {
                            labeled("Last run", "\(last.status.rawValue) · \(last.title)")
                        } else {
                            Text("No runs yet.")
                                .foregroundStyle(.secondary)
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.vertical, 4)
                }

                GroupBox("Tips") {
                    VStack(alignment: .leading, spacing: 6) {
                        Text("• On Compile: choose document-source, dataset-row, or mixed, add Sources, choose a Goal, then compile.")
                        Text("• Success is a sealed, independently verified .vfbundle — not file conversion and not a trainer handoff.")
                        Text("• On Review: wrap review-export, review-import, and review-submit. Default review_policy stays none.")
                        Text("• On Exports: choose that bundle, a generic container first, then operator-confirmed execute. The source bundle and receipt stay visible. The exporter does not train.")
                        Text("• Aptus is optional Integrations. It is not required.")
                        Text("• Output defaults to Documents/Veriformis (change in Settings).")
                        Text("• Install / CLI help: docs/install.md in the repo.")
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.vertical, 4)
                }

                Button {
                    workbench.destination = .compile
                } label: {
                    Label("Go to Compile", systemImage: "shippingbox.fill")
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.large)
            }
            .padding(24)
            .frame(maxWidth: 720, alignment: .leading)
        }
    }

    private func labeled(_ title: String, _ value: String) -> some View {
        HStack(alignment: .top) {
            Text(title)
                .foregroundStyle(.secondary)
                .frame(width: 80, alignment: .leading)
            Text(value)
                .textSelection(.enabled)
                .font(.system(.body, design: .monospaced))
        }
    }
}
