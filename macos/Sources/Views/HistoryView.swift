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
                if let stage = entry.failedStageTitle {
                    Text("·")
                    Text(stage)
                }
            }
            .font(.caption)
            .foregroundStyle(statusColor(entry.status))
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
                if let sha = entry.manifestSHA256 {
                    digestRow("Manifest SHA-256", sha, copyLabel: "manifest SHA-256")
                }
                if let digest = entry.assignmentDigest {
                    digestRow("Assignment digest", digest, copyLabel: "assignment digest")
                }
                if let digest = entry.transportArchiveSHA256 {
                    digestRow(
                        "Archive SHA-256",
                        digest,
                        copyLabel: "transport archive SHA-256"
                    )
                }
                if let stage = entry.failedStageTitle {
                    row(entry.status == .cancelled ? "Interrupted stage" : "Failed stage", stage)
                }
                if let code = entry.exitCode {
                    row("Exit code", String(code))
                }
                if let error = entry.errorSummary {
                    row("Error", error)
                }
                if let receipt = entry.cancellationReceipt {
                    GroupBox("Cancellation receipt") {
                        VStack(alignment: .leading, spacing: 6) {
                            row("Requested", receipt.requestedAt.formatted())
                            if let stage = receipt.stageTitle { row("Stage", stage) }
                            if let pid = receipt.processIdentifier { row("Process ID", String(pid)) }
                            if let status = receipt.terminationStatus { row("Termination", String(status)) }
                            row("Escalated", receipt.terminationEscalated ? "yes" : "no")
                            row("Workspace retained", receipt.workspaceRetained ? "yes" : "no")
                            row("Output truncated", receipt.outputWasTruncated ? "yes" : "no")
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(.vertical, 2)
                    }
                }

                if let notice = workbench.lastCopiedNotice {
                    Text(notice)
                        .font(.caption)
                        .foregroundStyle(.green)
                }

                if let handoff = entry.handoffPath {
                    GroupBox("Optional integrations") {
                        VStack(alignment: .leading, spacing: 8) {
                            row("Aptus handoff", handoff)
                            Button("Reveal handoff") {
                                workbench.reveal(URL(fileURLWithPath: handoff))
                            }
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(.vertical, 2)
                    }
                }

                HStack {
                    Button("Re-run") {
                        workbench.reRun(from: entry)
                    }
                    .buttonStyle(.borderedProminent)
                    Button("Reveal workspace") {
                        workbench.reveal(URL(fileURLWithPath: entry.workspacePath))
                    }
                    if let archive = entry.transportArchivePath {
                        Button("Reveal transport archive") {
                            workbench.reveal(URL(fileURLWithPath: archive))
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

    private func statusColor(_ status: RunStatus) -> Color {
        switch status {
        case .succeeded: return .secondary
        case .failed: return .red
        case .cancelled: return .orange
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
