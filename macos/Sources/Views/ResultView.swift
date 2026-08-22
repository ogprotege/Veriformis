import AppKit
import SwiftUI

struct ResultView: View {
    @EnvironmentObject private var workbench: WorkbenchViewModel
    let result: CompileResult

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Result")
                .font(.headline)

            gridRow("Workspace", result.workspaceURL.path)
            gridRow("Canonical bundle", result.bundleURL.path)
            gridRow("Transport archive", result.transportArchiveURL.path)
            if let sha = result.manifestSHA256 {
                digestRow(label: "Manifest SHA-256", value: sha, copyLabel: "manifest SHA-256")
            }
            if let digest = result.assignmentDigest {
                digestRow(label: "Assignment digest", value: digest, copyLabel: "assignment digest")
            }
            if let digest = result.transportArchiveSHA256 {
                digestRow(
                    label: "Archive SHA-256",
                    value: digest,
                    copyLabel: "transport archive SHA-256"
                )
            }

            if let notice = workbench.lastCopiedNotice {
                Text(notice)
                    .font(.caption)
                    .foregroundStyle(.green)
            }

            if let handoff = result.handoffURL {
                GroupBox("Optional integrations") {
                    VStack(alignment: .leading, spacing: 8) {
                        gridRow("Aptus handoff", handoff.path)
                        Button("Reveal handoff") {
                            workbench.reveal(handoff)
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.vertical, 2)
                }
            }

            GoalPreviewView(state: workbench.goalPreviewState)

            HStack {
                Button("Reveal workspace") {
                    workbench.reveal(result.workspaceURL)
                }
                Button("Reveal transport archive") {
                    workbench.reveal(result.transportArchiveURL)
                }
                if let log = result.logFileURL {
                    Button("Open log") {
                        workbench.openLogFile(log)
                    }
                }
                Button("Re-run") {
                    workbench.reRunLastConfiguration()
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.top, 8)
    }

    private func gridRow(_ label: String, _ value: String) -> some View {
        HStack(alignment: .top) {
            Text(label)
                .foregroundStyle(.secondary)
                .frame(width: 140, alignment: .leading)
            Text(value)
                .textSelection(.enabled)
                .font(.system(.body, design: .monospaced))
        }
    }

    private func digestRow(label: String, value: String, copyLabel: String) -> some View {
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

/// Shows exactly what each record is and which region receives loss (Phase 6.3).
struct GoalPreviewView: View {
    let state: GoalPreviewState

    var body: some View {
        GroupBox("What the model will learn") {
            VStack(alignment: .leading, spacing: 10) {
                switch state {
                case .idle:
                    Text("Preview is available after a compile.")
                        .foregroundStyle(.secondary)
                case .loading:
                    ProgressView("Loading goal preview…")
                case .unavailable(let message):
                    Text(message)
                        .foregroundStyle(.secondary)
                        .textSelection(.enabled)
                case .ready(let preview):
                    previewBody(preview)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.vertical, 2)
        }
    }

    @ViewBuilder
    private func previewBody(_ preview: GoalPreview) -> some View {
        Text(preview.title)
            .font(.headline)
        Text(preview.supervisionBoundary)
        Text("\(preview.supervisedRegion) (\(preview.lossPolicy))")
            .font(.caption)
            .foregroundStyle(.secondary)
        ForEach(preview.notThis, id: \.self) { claim in
            Text("Not this: \(claim)")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        if let counts = countsLine(preview.counts) {
            Text(counts)
                .font(.caption.monospaced())
                .foregroundStyle(.secondary)
        }
        ForEach(preview.records, id: \.recordID) { record in
            recordView(record)
        }
        if !preview.exclusions.isEmpty {
            Text("Excluded records")
                .font(.subheadline.weight(.semibold))
            ForEach(preview.exclusions, id: \.recordID) { exclusion in
                Text("\(exclusion.status): \(exclusion.reasonCodes.joined(separator: ", "))")
                    .font(.caption.monospaced())
                    .textSelection(.enabled)
            }
            if preview.omittedExclusionCount > 0 {
                Text("\(preview.omittedExclusionCount) more exclusions omitted from this preview.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        if !preview.diagnostics.isEmpty {
            Text("Why some sources produced nothing")
                .font(.subheadline.weight(.semibold))
            ForEach(Array(preview.diagnostics.enumerated()), id: \.offset) { _, diagnostic in
                Text("\(diagnostic.code): \(diagnostic.message)")
                    .font(.caption)
                    .textSelection(.enabled)
            }
        }
    }

    @ViewBuilder
    private func recordView(_ record: GoalPreviewRecord) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(record.logicalPaths.joined(separator: ", "))
                .font(.caption.monospaced())
                .foregroundStyle(.secondary)
            if let omission = record.omissionReason {
                Text("Row omitted: \(omission)")
                    .font(.caption)
                    .foregroundStyle(.orange)
            }
            if let context = record.context, !context.isEmpty {
                ForEach(context.keys.sorted(), id: \.self) { key in
                    labeled("Context · \(key)", context[key] ?? "")
                }
            }
            if let target = record.target {
                ForEach(target.keys.sorted(), id: \.self) { key in
                    labeled("Target · \(key)", target[key] ?? "")
                }
            }
            if let value = record.supervisedValue {
                VStack(alignment: .leading, spacing: 2) {
                    Text("Trained on: \(plainSupervisedLabel(record.supervised.rowKey)) (\(record.supervised.end) code points)")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Text(value)
                        .font(.body.monospaced())
                        .padding(6)
                        .background(Color.accentColor.opacity(0.15))
                        .textSelection(.enabled)
                }
            }
            if let status = record.curationStatus {
                Text("Curation: \(status) \(record.curationReasonCodes.joined(separator: ", "))")
                    .font(.caption.monospaced())
            }
        }
        .padding(.vertical, 4)
    }

    private func plainSupervisedLabel(_ rowKey: String) -> String {
        switch rowKey {
        case "text": return "the whole text"
        case "completion": return "the completion"
        case "output": return "the output"
        case "messages[1].content": return "the assistant turn"
        default: return rowKey
        }
    }

    private func labeled(_ label: String, _ value: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(label)
                .font(.caption)
                .foregroundStyle(.secondary)
            Text(value)
                .font(.body.monospaced())
                .textSelection(.enabled)
        }
    }

    private func countsLine(_ counts: [String: Int]) -> String? {
        guard !counts.isEmpty else { return nil }
        return counts.keys.sorted().map { "\($0)=\(counts[$0] ?? 0)" }.joined(separator: "  ")
    }
}
