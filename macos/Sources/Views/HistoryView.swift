import SwiftUI

struct HistoryView: View {
    @EnvironmentObject private var workbench: WorkbenchViewModel

    var body: some View {
        HSplitView {
            List(workbench.runHistory, id: \.id, selection: $workbench.selectedHistoryID) { entry in
                historyRow(entry)
            }
            .frame(minWidth: 240, idealWidth: 280)

            Group {
                if let entry = workbench.selectedHistoryEntry {
                    historyDetail(entry)
                } else {
                    Text("No runs yet.\nSuccessful and failed compiles appear here.")
                        .foregroundStyle(.secondary)
                        .multilineTextAlignment(.center)
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .padding(8)
    }

    private func historyRow(_ entry: RunHistoryEntry) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(entry.title)
                .font(.body.weight(.medium))
            HStack(spacing: 6) {
                Text(entry.status.rawValue)
                Text("·")
                Text(entry.objective)
                if let stage = entry.failedStage {
                    Text("·")
                    Text(stage)
                }
            }
            .font(.caption)
            .foregroundStyle(entry.status == .succeeded ? Color.secondary : Color.red)
        }
        .tag(entry.id as UUID?)
    }

    private func historyDetail(_ entry: RunHistoryEntry) -> some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                Text("Run detail")
                    .font(.title2.weight(.semibold))
                row("Status", entry.status.rawValue)
                row("Objective", entry.objective)
                row("Source", entry.primarySourceName)
                row("Workspace", entry.workspacePath)
                row("Bundle", entry.bundlePath)
                if let handoff = entry.handoffPath {
                    row("Aptus handoff", handoff)
                }
                if let sha = entry.manifestSHA256 {
                    digestRow("Manifest SHA-256", sha, copyLabel: "manifest SHA-256")
                }
                if let digest = entry.assignmentDigest {
                    digestRow("Assignment digest", digest, copyLabel: "assignment digest")
                }
                if let stage = entry.failedStage {
                    row("Failed stage", stage)
                }
                if let code = entry.exitCode {
                    row("Exit code", String(code))
                }
                if let error = entry.errorSummary {
                    row("Error", error)
                }

                if let notice = workbench.lastCopiedNotice {
                    Text(notice)
                        .font(.caption)
                        .foregroundStyle(.green)
                }

                HStack {
                    Button("Re-run") {
                        workbench.reRun(from: entry)
                    }
                    .buttonStyle(.borderedProminent)
                    Button("Reveal workspace") {
                        workbench.reveal(URL(fileURLWithPath: entry.workspacePath))
                    }
                    Button("Reveal bundle") {
                        workbench.reveal(URL(fileURLWithPath: entry.bundlePath))
                    }
                    if let handoff = entry.handoffPath {
                        Button("Reveal handoff") {
                            workbench.reveal(URL(fileURLWithPath: handoff))
                        }
                    }
                    if let log = entry.logFilePath {
                        Button("Open log") {
                            workbench.openLogFile(URL(fileURLWithPath: log))
                        }
                    }
                }
                .padding(.top, 8)
            }
            .padding(20)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private func row(_ label: String, _ value: String) -> some View {
        HStack(alignment: .top) {
            Text(label)
                .foregroundStyle(.secondary)
                .frame(width: 140, alignment: .leading)
            Text(value)
                .textSelection(.enabled)
                .font(.system(.body, design: .monospaced))
        }
    }

    private func digestRow(_ label: String, _ value: String, copyLabel: String) -> some View {
        HStack(alignment: .top) {
            Text(label)
                .foregroundStyle(.secondary)
                .frame(width: 140, alignment: .leading)
            Text(value)
                .textSelection(.enabled)
                .font(.system(.body, design: .monospaced))
            Button("Copy") {
                workbench.copyToPasteboard(value, label: copyLabel)
            }
            .buttonStyle(.borderless)
        }
    }
}
