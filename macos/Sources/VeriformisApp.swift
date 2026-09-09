import AppKit
import SwiftUI

@MainActor
final class ApplicationTerminationCoordinator {
    private(set) var awaitingCancellation = false

    func prepareForTermination(
        isRunActive: Bool,
        cancel: (@escaping () -> Void) -> Void,
        reply: @escaping () -> Void
    ) -> NSApplication.TerminateReply {
        guard !awaitingCancellation else { return .terminateLater }
        guard isRunActive else { return .terminateNow }
        awaitingCancellation = true
        cancel { [weak self] in
            guard let self, self.awaitingCancellation else { return }
            self.awaitingCancellation = false
            reply()
        }
        return .terminateLater
    }
}

@MainActor
final class VeriformisAppDelegate: NSObject, NSApplicationDelegate {
    weak var workbench: WorkbenchViewModel?
    private let terminationCoordinator = ApplicationTerminationCoordinator()

    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        terminationCoordinator.prepareForTermination(
            isRunActive: workbench?.hasActiveOperations == true,
            cancel: { [weak workbench] completion in
                if let workbench { workbench.cancelAllOperations(onFinished: completion) }
                else { completion() }
            },
            reply: { [weak sender] in
                sender?.reply(toApplicationShouldTerminate: true)
            }
        )
    }

    func applicationWillTerminate(_ notification: Notification) {
        workbench?.cancelAllOperations(onFinished: {})
    }
}

@main
struct VeriformisApp: App {
    @NSApplicationDelegateAdaptor(VeriformisAppDelegate.self) private var appDelegate
    @StateObject private var workbench = WorkbenchViewModel()

    var body: some Scene {
        WindowGroup("Veriformis Workbench") {
            ContentView()
                .environmentObject(workbench)
                .frame(minWidth: 960, minHeight: 640)
                .onAppear {
                    appDelegate.workbench = workbench
                }
        }
        .commands {
            CommandGroup(replacing: .newItem) {}
            CommandMenu("Go") {
                Button("Home") { workbench.destination = .home }
                    .keyboardShortcut("1", modifiers: .command)
                Button("Compile") { workbench.destination = .compile }
                    .keyboardShortcut("2", modifiers: .command)
                Button("Review") { workbench.destination = .review }
                    .keyboardShortcut("3", modifiers: .command)
                Button("Exports") { workbench.destination = .exports }
                    .keyboardShortcut("4", modifiers: .command)
                Button("History") { workbench.destination = .history }
                    .keyboardShortcut("5", modifiers: .command)
                Button("Settings") { workbench.destination = .settings }
                    .keyboardShortcut("6", modifiers: .command)
            }
            CommandMenu("Compile") {
                Button("Compile to sealed bundle") { workbench.compile() }
                    .keyboardShortcut(.return, modifiers: .command)
                    .disabled(!workbench.canCompile)
                Button("Cancel compile") { workbench.cancelCompile() }
                    .keyboardShortcut(".", modifiers: .command)
                    .disabled(!workbench.isRunning)
                Button("Copy compile CLI equivalent") {
                    if let text = workbench.currentCompileCLIEquivalent {
                        workbench.copyToPasteboard(text, label: "CLI equivalent")
                    }
                }
                .keyboardShortcut("c", modifiers: [.command, .shift])
                .disabled(workbench.currentCompileCLIEquivalent == nil)
            }
        }
    }
}
