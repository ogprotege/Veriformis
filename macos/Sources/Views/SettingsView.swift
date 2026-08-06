import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var workbench: WorkbenchViewModel

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                Text("Settings")
                    .font(.title2.weight(.semibold))

                GroupBox("Compiler CLI") {
                    VStack(alignment: .leading, spacing: 10) {
                        Text("Resolved")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                        Text(workbench.resolvedCLIDescription)
                            .font(.system(.body, design: .monospaced))
                            .textSelection(.enabled)

                        Text("Optional absolute path override (persisted)")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                        TextField("/path/to/veriformis", text: $workbench.cliOverridePath)
                            .textFieldStyle(.roundedBorder)

                        HStack {
                            Button("Apply override") { workbench.saveCLIOverride() }
                            Button("Clear override") { workbench.clearCLIOverride() }
                            Button("Re-detect CLI") { workbench.bootstrapCLI() }
                        }

                        Text("GUI apps often lack your Terminal PATH. Prefer bash macos/scripts/run_workbench.sh or docs/install.md.")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.vertical, 4)
                }

                GroupBox("Default output folder") {
                    VStack(alignment: .leading, spacing: 10) {
                        Text(workbench.defaultOutputPath.isEmpty ? "(not set)" : workbench.defaultOutputPath)
                            .font(.system(.body, design: .monospaced))
                            .textSelection(.enabled)
                        Button("Choose default…") { workbench.chooseDefaultOutputDirectory() }
                        Text("Used on Compile when no folder is selected yet. Defaults to ~/Documents/Veriformis.")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.vertical, 4)
                }
            }
            .padding(24)
            .frame(maxWidth: 720, alignment: .leading)
        }
    }
}
