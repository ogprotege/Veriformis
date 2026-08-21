import SwiftUI

struct HomeView: View {
    @EnvironmentObject private var workbench: WorkbenchViewModel

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                Text("Veriformis")
                    .font(.largeTitle.weight(.semibold))
                Text("Dataset compiler — private beta workbench")
                    .foregroundStyle(.secondary)

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
                        Text("• Start with one source file on Compile.")
                        Text("• Output defaults to Documents/Veriformis (change in Settings).")
                        Text("• Success means a sealed .vfbundle — not general-purpose file conversion.")
                        Text("• Choose the training objective that matches the rows your trainer expects.")
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
