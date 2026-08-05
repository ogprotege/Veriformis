import SwiftUI
import UniformTypeIdentifiers

struct ContentView: View {
    @EnvironmentObject private var workbench: WorkbenchViewModel

    var body: some View {
        NavigationSplitView {
            VStack(alignment: .leading, spacing: 16) {
                Text("Veriformis")
                    .font(.title2.weight(.semibold))
                Text("Dataset workbench")
                    .foregroundStyle(.secondary)

                Divider()

                SourceDropView()

                Divider()

                configurationPanel

                Spacer()

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
            }
            .padding()
            .frame(minWidth: 300)
        } detail: {
            VStack(spacing: 0) {
                StagePanelView()
                    .padding()
                Divider()
                LogView()
                if let result = workbench.lastResult {
                    Divider()
                    ResultView(result: result)
                        .padding()
                }
            }
        }
        .onAppear {
            workbench.bootstrapCLI()
        }
        .alert(
            "Workbench error",
            isPresented: Binding(
                get: { workbench.lastError != nil },
                set: { if !$0 { workbench.lastError = nil } }
            )
        ) {
            Button("OK", role: .cancel) { workbench.lastError = nil }
        } message: {
            Text(workbench.lastError ?? "")
        }
    }

    private var configurationPanel: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Configuration")
                .font(.headline)

            Picker("Objective", selection: $workbench.objective) {
                ForEach(TrainingObjective.allCases) { objective in
                    Text(objective.title).tag(objective)
                }
            }

            if workbench.objective == .continuation {
                HStack {
                    Text("Split ratio (ppm)")
                    TextField(
                        "400000",
                        value: $workbench.splitRatioPPM,
                        format: .number
                    )
                    .textFieldStyle(.roundedBorder)
                    .frame(width: 100)
                }
            }

            Toggle("Allow empty evaluation", isOn: $workbench.allowEmptyEvaluation)
            Toggle("Write Aptus handoff", isOn: $workbench.writeAptusHandoff)

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
        }
    }
}
