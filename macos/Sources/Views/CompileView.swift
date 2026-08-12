import SwiftUI

struct CompileView: View {
    @EnvironmentObject private var workbench: WorkbenchViewModel
    @State private var showAdvanced = false
    @State private var showIntegrations = false

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

            VStack(alignment: .leading, spacing: 4) {
                Picker("Objective", selection: $workbench.objective) {
                    ForEach(TrainingObjective.allCases) { objective in
                        Text(objective.title).tag(objective)
                    }
                }
                Text(workbench.objective.subtitle)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }

            if workbench.objective == .continuation {
                HStack {
                    Text("Train share (ppm)")
                    TextField(
                        "500000",
                        value: $workbench.splitRatioPPM,
                        format: .number
                    )
                    .textFieldStyle(.roundedBorder)
                    .frame(width: 100)
                }
                Text("Parts per million of rows for train (500000 ≈ 50% train, the CLI default).")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Toggle("Allow empty evaluation partition", isOn: $workbench.allowEmptyEvaluation)
            Text("Off by default: compiles fail closed when evaluation would be empty, matching the CLI. Enable only when a single leakage group leaves evaluation empty.")
                .font(.caption)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)

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
}
