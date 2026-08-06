import SwiftUI

struct RunSheetView: View {
    @EnvironmentObject private var workbench: WorkbenchViewModel

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text(title)
                .font(.title3.weight(.semibold))

            if workbench.isRunning {
                if let stage = workbench.currentStage {
                    Text("Stage: \(stage.title)")
                        .foregroundStyle(.secondary)
                } else {
                    Text("Starting…")
                        .foregroundStyle(.secondary)
                }
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

            if let failure = workbench.lastFailure, !workbench.isRunning {
                failurePanel(failure)
            }

            if let result = workbench.lastResult, !workbench.isRunning {
                successDigestPanel(result)
            }

            if let notice = workbench.lastCopiedNotice, !workbench.isRunning {
                Text(notice)
                    .font(.caption)
                    .foregroundStyle(.green)
            }

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

            HStack {
                if !workbench.isRunning {
                    Button("Re-run") {
                        workbench.reRunLastConfiguration()
                    }
                    .disabled(workbench.sourceURLs.isEmpty && workbench.runHistory.isEmpty)
                }
                Spacer()
                if !workbench.isRunning {
                    if let result = workbench.lastResult {
                        Button("Reveal workspace") {
                            workbench.reveal(result.workspaceURL)
                        }
                        Button("Reveal bundle") {
                            workbench.reveal(result.bundleURL)
                        }
                    } else if let workspace = workbench.lastFailure?.workspaceURL {
                        Button("Reveal workspace") {
                            workbench.reveal(workspace)
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
        if workbench.lastFailure != nil { return "Compile failed" }
        if workbench.lastResult != nil { return "Compile complete" }
        return "Compile"
    }

    private func failurePanel(_ failure: CompileFailure) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(failure.summary)
                .font(.body.weight(.semibold))
                .foregroundStyle(.red)
            if let code = failure.exitCode {
                Text("Exit code: \(code)")
                    .font(.caption.monospaced())
            }
            Text("Stage: \(failure.stage)")
                .font(.caption)
                .foregroundStyle(.secondary)

            if !failure.lastLogLines.isEmpty {
                Text("Last log lines")
                    .font(.caption.weight(.semibold))
                VStack(alignment: .leading, spacing: 2) {
                    ForEach(Array(failure.lastLogLines.enumerated()), id: \.offset) { _, line in
                        Text(line)
                            .font(.system(.caption2, design: .monospaced))
                            .textSelection(.enabled)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                }
                .padding(8)
                .background(Color.red.opacity(0.08))
                .clipShape(RoundedRectangle(cornerRadius: 6))
            }

            HStack {
                Button("Copy error") {
                    workbench.copyToPasteboard(
                        failure.summary + "\n" + failure.message,
                        label: "error"
                    )
                }
                if let log = failure.logFileURL {
                    Button("Open log") {
                        workbench.openLogFile(log)
                    }
                }
            }
        }
        .padding(10)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.red.opacity(0.06))
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }

    private func successDigestPanel(_ result: CompileResult) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            if let sha = result.manifestSHA256 {
                HStack {
                    Text("Manifest SHA-256")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Spacer()
                    Button("Copy") {
                        workbench.copyToPasteboard(sha, label: "manifest SHA-256")
                    }
                    .buttonStyle(.borderless)
                }
                Text(sha)
                    .font(.system(.caption, design: .monospaced))
                    .textSelection(.enabled)
            }
            if let digest = result.assignmentDigest {
                HStack {
                    Text("Assignment digest")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Spacer()
                    Button("Copy") {
                        workbench.copyToPasteboard(digest, label: "assignment digest")
                    }
                    .buttonStyle(.borderless)
                }
                Text(digest)
                    .font(.system(.caption, design: .monospaced))
                    .textSelection(.enabled)
            }
        }
        .padding(10)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.green.opacity(0.08))
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }
}
