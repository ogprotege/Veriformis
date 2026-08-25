import AppKit
import SwiftUI
import UniformTypeIdentifiers

struct SourceDropView: View {
    @EnvironmentObject private var workbench: WorkbenchViewModel
    @State private var isTargeted = false

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Sources")
                .font(.headline)

            ZStack {
                RoundedRectangle(cornerRadius: 12)
                    .strokeBorder(
                        isTargeted ? Color.accentColor : Color.secondary.opacity(0.35),
                        style: StrokeStyle(lineWidth: 2, dash: [8])
                    )
                    .background(
                        RoundedRectangle(cornerRadius: 12)
                            .fill(isTargeted ? Color.accentColor.opacity(0.08) : Color.clear)
                    )

                VStack(spacing: 8) {
                    Image(systemName: "arrow.down.doc")
                        .font(.system(size: 28, weight: .light))
                        .foregroundStyle(.secondary)
                    Text("Drop files or folders here")
                        .font(.callout.weight(.medium))
                    Text("txt · md · docx · html · pdf · csv · json · jsonl · code")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Button("Browse…") { openPanel() }
                        .buttonStyle(.bordered)
                }
                .padding()
            }
            .frame(minHeight: 140)
            .onDrop(of: [.fileURL], isTargeted: $isTargeted, perform: handleDrop)

            if !workbench.sourceURLs.isEmpty {
                List {
                    ForEach(workbench.sourceURLs, id: \.path) { url in
                        HStack {
                            Image(systemName: "doc")
                            Text(url.lastPathComponent)
                            Spacer()
                            Text(url.pathExtension.uppercased())
                                .font(.caption2)
                                .foregroundStyle(.secondary)
                            Button(role: .destructive) {
                                workbench.removeSource(url)
                            } label: {
                                Image(systemName: "xmark.circle.fill")
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }
                .frame(minHeight: 100, maxHeight: 180)
                .listStyle(.inset)

                Button("Clear sources", role: .destructive) {
                    workbench.clearSources()
                }
                .buttonStyle(.plain)
            }
        }
    }

    private func openPanel() {
        let panel = NSOpenPanel()
        panel.allowsMultipleSelection = true
        panel.canChooseFiles = true
        panel.canChooseDirectories = true
        panel.allowedContentTypes = Self.supportedTypes
        if panel.runModal() == .OK {
            workbench.addSources(expand(panel.urls))
        }
    }

    private func handleDrop(_ providers: [NSItemProvider]) -> Bool {
        var urls: [URL] = []
        let group = DispatchGroup()
        for provider in providers {
            group.enter()
            provider.loadItem(forTypeIdentifier: UTType.fileURL.identifier, options: nil) { item, _ in
                defer { group.leave() }
                if let data = item as? Data,
                   let path = String(data: data, encoding: .utf8),
                   let url = URL(string: path)
                {
                    urls.append(url)
                } else if let url = item as? URL {
                    urls.append(url)
                }
            }
        }
        group.notify(queue: .main) {
            workbench.addSources(expand(urls))
        }
        return true
    }

    private func expand(_ urls: [URL]) -> [URL] {
        // Collection membership is PipelineService. The workbench passes files
        // and directories through unchanged so CLI parse/collect expand them.
        let fm = FileManager.default
        return urls.filter { url in
            var isDir: ObjCBool = false
            if fm.fileExists(atPath: url.path, isDirectory: &isDir), isDir.boolValue {
                return true
            }
            return supported(url)
        }
    }

    private func supported(_ url: URL) -> Bool {
        let ext = url.pathExtension.lowercased()
        return Self.extensions.contains(ext)
    }

    private static let extensions: Set<String> = [
        "txt", "md", "markdown", "docx", "html", "htm", "pdf", "csv", "json", "jsonl",
        "py", "js", "ts", "java", "c", "cpp", "go", "rs", "rb", "sh",
    ]

    private static let supportedTypes: [UTType] = [
        .plainText, .utf8PlainText, .sourceCode, .pythonScript, .javaScript,
        .html, .pdf, .commaSeparatedText, .json, .data, .item, .folder,
    ]
}
