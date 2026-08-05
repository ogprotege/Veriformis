import SwiftUI

@main
struct VeriformisApp: App {
    @StateObject private var workbench = WorkbenchViewModel()

    var body: some Scene {
        WindowGroup("Veriformis Workbench") {
            ContentView()
                .environmentObject(workbench)
                .frame(minWidth: 960, minHeight: 640)
        }
        .commands {
            CommandGroup(replacing: .newItem) {}
        }
    }
}
