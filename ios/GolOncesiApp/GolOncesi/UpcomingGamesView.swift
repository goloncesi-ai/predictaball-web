import SwiftUI

@MainActor
final class UpcomingGamesViewModel: ObservableObject {
    private enum Keys {
        static let round = "upcoming.round"
    }

    private let defaults = UserDefaults.standard

    @Published var isLoading = false
    @Published var errorMessage: String?
    @Published var round = 1 { didSet { defaults.set(round, forKey: Keys.round) } }
    @Published var matches: [RecentGame] = []

    init() {
        let stored = defaults.integer(forKey: Keys.round)
        round = stored == 0 ? 1 : stored
    }

    func loadInitial() async {
        do {
            let payload = try await APIClient.shared.loadCurrentRound()
            round = payload.currentRound
        } catch {
            round = 19
        }
        await loadRound(round)
    }

    func loadRound(_ round: Int) async {
        isLoading = true
        errorMessage = nil

        do {
            let payload = try await APIClient.shared.loadRecentGames(round: round)
            self.round = payload.round
            matches = payload.matches
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }
}

struct UpcomingGamesView: View {
    @StateObject private var vm = UpcomingGamesViewModel()

    var body: some View {
        NavigationStack {
            List {
                Section {
                    Stepper(value: $vm.round, in: 1...34) {
                        Text("Round \(vm.round)")
                    }
                    .onChange(of: vm.round) { value in
                        Task { await vm.loadRound(value) }
                    }
                }

                if vm.matches.isEmpty && !vm.isLoading {
                    Section {
                        Text("No matches found for this round.")
                            .foregroundStyle(.secondary)
                    }
                }

                ForEach(vm.matches) { match in
                    VStack(alignment: .leading, spacing: 10) {
                        HStack(alignment: .top) {
                            VStack(alignment: .leading, spacing: 4) {
                                Text("\(match.homeTeam) vs \(match.awayTeam)")
                                    .font(.headline)
                                HStack {
                                    if let date = match.date {
                                        Label(date, systemImage: "calendar")
                                    }
                                    if let time = match.time {
                                        Label(time, systemImage: "clock")
                                    }
                                }
                                .font(.caption)
                                .foregroundStyle(.secondary)
                            }

                            Spacer()

                            if let status = match.status {
                                Text(status)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                        }

                        if let prediction = match.prediction {
                            if let score = prediction.predictedScore {
                                Text("Predicted Score: \(score)")
                                    .font(.subheadline)
                                    .fontWeight(.medium)
                            }

                            if let conf = prediction.confidence {
                                Text("Confidence: \(conf.capitalized)")
                                    .font(.caption)
                                    .fontWeight(.semibold)
                                    .foregroundStyle(confidenceColor(conf))
                            }

                            if let probs = prediction.probabilities {
                                VStack(spacing: 6) {
                                    probabilityRow("Home", probs.homeWin, .blue)
                                    probabilityRow("Draw", probs.draw, .orange)
                                    probabilityRow("Away", probs.awayWin, .red)
                                }
                            }

                            if let xg = prediction.expectedGoals,
                               let homeXg = xg.home,
                               let awayXg = xg.away {
                                Text(String(format: "xG: %.2f - %.2f", homeXg, awayXg))
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }

                            let top5 = prediction.topScorelinesHomePerspective.isEmpty
                                ? prediction.topScorelines
                                : prediction.topScorelinesHomePerspective
                            if !top5.isEmpty {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text("Top Scorelines")
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                    ForEach(top5.prefix(3)) { row in
                                        HStack {
                                            Text(row.score)
                                            Spacer()
                                            Text(String(format: "%.1f%%", row.percentage))
                                                .foregroundStyle(.secondary)
                                        }
                                        .font(.caption)
                                    }
                                }
                            }
                        }
                    }
                    .padding(.vertical, 6)
                }
            }
            .navigationTitle("Upcoming Games")
            .overlay {
                if vm.isLoading {
                    ProgressView("Loading games...")
                }
            }
            .task { await vm.loadInitial() }
            .refreshable {
                await vm.loadRound(vm.round)
            }
            .alert("Error", isPresented: .constant(vm.errorMessage != nil), presenting: vm.errorMessage) { _ in
                Button("OK") { vm.errorMessage = nil }
            } message: { message in
                Text(message)
            }
        }
    }

    private func probabilityRow(_ label: String, _ value: Double?, _ color: Color) -> some View {
        VStack(alignment: .leading, spacing: 3) {
            HStack {
                Text(label)
                Spacer()
                Text(percent(value))
                    .foregroundStyle(.secondary)
            }
            ProgressView(value: max(min(value ?? 0, 100), 0), total: 100)
                .tint(color)
        }
        .font(.caption)
    }

    private func confidenceColor(_ confidence: String) -> Color {
        switch confidence.lowercased() {
        case "high": return .green
        case "low": return .red
        default: return .orange
        }
    }

    private func percent(_ value: Double?) -> String {
        guard let value else { return "-" }
        return String(format: "%.1f%%", value)
    }
}

#Preview {
    UpcomingGamesView()
}
