import SwiftUI

struct ContentView: View {
    @EnvironmentObject private var workbench: WorkbenchViewModel

    var body: some View {
        NavigationSplitView {
            List(SidebarDestination.allCases, selection: Binding(
                get: { workbench.destination },
                set: { workbench.destination = $0 ?? .compile }
            )) { item in
                Label(item.title, systemImage: item.systemImage)
                    .tag(item)
            }
            .navigationSplitViewColumnWidth(min: 160, ideal: 180, max: 220)
            .listStyle(.sidebar)
        } detail: {
            switch workbench.destination {
            case .home:
                HomeView()
            case .compile:
                CompileView()
            case .history:
                HistoryView()
            case .settings:
                SettingsView()
            }
        }
        .onAppear {
            workbench.bootstrapCLI()
        }
        .sheet(isPresented: $workbench.showRunSheet) {
            RunSheetView()
                .frame(minWidth: 560, minHeight: 420)
        }
        .alert(
            "Workbench error",
            isPresented: Binding(
                get: { workbench.lastError != nil && !workbench.showRunSheet },
                set: { if !$0 { workbench.lastError = nil } }
            )
        ) {
            Button("OK", role: .cancel) { workbench.lastError = nil }
        } message: {
            Text(workbench.lastError ?? "")
        }
    }
}
