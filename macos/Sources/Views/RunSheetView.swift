import SwiftUI

struct RunSheetView: View {
    @EnvironmentObject private var workbench: WorkbenchViewModel

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text(title)
                .font(.title3.weight(.semibold))

            if let stage = workbench.currentStage {
                Text("Stage: \(stage.title)")
                    .foregroundStyle(.secondary)
            } else if workbench.isRunning {
                Text("Starting…")
                    .foregroundStyle(.secondary)
            } else {
                Text(workbench.runStatusMessage)
                    .foregroundStyle(.secondary)
            }

            ProgressView(value: workbench.progressPercent, total: 100) {
                Text("Progress")
            } currentValueLabel: {
                Text("\(Int(workbench.progressPercent.rounded()))%")
                    .monospacedDigit()
            }

            StagePanelView()

            DisclosureGroup(isExpanded: $workbench.logExpanded) {
                ScrollViewReader { proxy in
                    ScrollView {
                        LazyVStack(alignment: .leading, spacing: 2) {
                            ForEach(Array(workbench.logLines.enumerated()), id: \.offset) { index, line in
                                Text(line)
                                    .font(.system(.caption, design: .monospaced))
                                    .frame(maxWidth: .infinity, alignment: .leading)
                                    .textSelection(.enabled)
                                    .id(index)
                            }
                        }
                        .padding(8)
                    }
                    .frame(minHeight: 180, maxHeight: 320)
                    .background(Color(nsColor: .textBackgroundColor))
                    .clipShape(RoundedRectangle(cornerRadius: 8))
                    .onChange(of: workbench.logLines.count) { _, _ in
                        if let last = workbench.logLines.indices.last {
                            proxy.scrollTo(last, anchor: .bottom)
                        }
                    }
                }
            } label: {
                Text(workbench.logExpanded ? "Hide log" : "Show log")
            }

            if let error = workbench.lastError, !workbench.isRunning {
                Text(error)
                    .font(.caption)
                    .foregroundStyle(.red)
                    .textSelection(.enabled)
            }

            HStack {
                Spacer()
                if !workbench.isRunning {
                    if let result = workbench.lastResult {
                        Button("Reveal bundle") {
                            workbench.reveal(result.bundleURL)
                        }
                    }
                    Button("Close") {
                        workbench.showRunSheet = false
                    }
                    .keyboardShortcut(.defaultAction)
                }
            }
        }
        .padding(20)
    }

    private var title: String {
        if workbench.isRunning { return "Compiling…" }
        if workbench.lastError != nil { return "Compile failed" }
        if workbench.lastResult != nil { return "Compile complete" }
        return "Compile"
    }
}
