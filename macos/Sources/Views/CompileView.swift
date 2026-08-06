import SwiftUI

struct CompileView: View {
    @EnvironmentObject private var workbench: WorkbenchViewModel
    @State private var showAdvanced = false

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
                        "400000",
                        value: $workbench.splitRatioPPM,
                        format: .number
                    )
                    .textFieldStyle(.roundedBorder)
                    .frame(width: 100)
                }
                Text("Parts per million of rows for train (400000 ≈ 40% train).")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Toggle("Allow empty evaluation partition", isOn: $workbench.allowEmptyEvaluation)
            Text("Needed when a single leakage group leaves evaluation empty.")
                .font(.caption)
                .foregroundStyle(.secondary)

            Toggle("Write Aptus handoff file", isOn: $workbench.writeAptusHandoff)
            Text("Sibling descriptor for training consumers. Plain text rows may still be rejected by Aptus.")
                .font(.caption)
                .foregroundStyle(.secondary)

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
