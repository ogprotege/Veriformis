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
            gridRow("Bundle", result.bundleURL.path)
            if let handoff = result.handoffURL {
                gridRow("Aptus handoff", handoff.path)
            }
            if let sha = result.manifestSHA256 {
                gridRow("Manifest SHA-256", sha)
            }

            HStack {
                Button("Reveal workspace") {
                    workbench.reveal(result.workspaceURL)
                }
                Button("Reveal bundle") {
                    workbench.reveal(result.bundleURL)
                }
                if let handoff = result.handoffURL {
                    Button("Reveal handoff") {
                        workbench.reveal(handoff)
                    }
                }
                if let log = result.logFileURL {
                    Button("Open log") {
                        workbench.openLogFile(log)
                    }
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
}
