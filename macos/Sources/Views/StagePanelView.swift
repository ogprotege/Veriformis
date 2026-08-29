import SwiftUI

struct StagePanelView: View {
    @EnvironmentObject private var workbench: WorkbenchViewModel

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Pipeline")
                .font(.headline)

            // Wrap-friendly layout for nine stages.
            LazyVGrid(
                columns: [GridItem(.adaptive(minimum: 72), spacing: 8)],
                alignment: .leading,
                spacing: 8
            ) {
                ForEach(workbench.currentPipelineStages) { stage in
                    stageChip(stage)
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func stageChip(_ stage: WorkbenchStage) -> some View {
        let done = workbench.completedStages.contains(stage)
        let active = workbench.currentStage == stage
        return Text(stage.title)
            .font(.caption.weight(.semibold))
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(
                Capsule().fill(
                    active ? Color.accentColor.opacity(0.25)
                        : done ? Color.green.opacity(0.18)
                        : Color.secondary.opacity(0.12)
                )
            )
            .overlay(
                Capsule().stroke(
                    active ? Color.accentColor : Color.clear,
                    lineWidth: 1
                )
            )
    }
}
