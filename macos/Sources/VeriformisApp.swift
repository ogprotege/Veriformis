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
        guard isRunActive else { return .terminateNow }
        guard !awaitingCancellation else { return .terminateLater }
        awaitingCancellation = true
        cancel { [weak self] in
            self?.awaitingCancellation = false
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
            isRunActive: workbench?.isRunning == true,
            cancel: { [weak workbench] completion in
                workbench?.cancelCompile(onFinished: completion)
            },
            reply: { [weak sender] in
                sender?.reply(toApplicationShouldTerminate: true)
            }
        )
    }

    func applicationWillTerminate(_ notification: Notification) {
        workbench?.cancelCompile()
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
        }
    }
}
