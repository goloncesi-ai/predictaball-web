import SwiftUI

@MainActor
final class AnalysisViewModel: ObservableObject {
    private enum Keys {
        static let selectedHomeTeam = "analysis.selectedHomeTeam"
        static let selectedAwayTeam = "analysis.selectedAwayTeam"
    }

    private let defaults = UserDefaults.standard

    @Published var isLoading = false
    @Published var errorMessage: String?
    @Published var teams: [AnalysisTeam] = []
    @Published var selectedHomeTeam = "" { didSet { defaults.set(selectedHomeTeam, forKey: Keys.selectedHomeTeam) } }
    @Published var selectedAwayTeam = "" { didSet { defaults.set(selectedAwayTeam, forKey: Keys.selectedAwayTeam) } }

    enum RankingMetric: String, CaseIterable, Identifiable {
        case goalsScored = "Goals Scored"
        case goalsConceded = "Goals Conceded"
        case winRate = "Win Rate"
        case possession = "Possession"

        var id: String { rawValue }
    }

    init() {
        selectedHomeTeam = defaults.string(forKey: Keys.selectedHomeTeam) ?? ""
        selectedAwayTeam = defaults.string(forKey: Keys.selectedAwayTeam) ?? ""
    }

    func load() async {
        isLoading = true
        errorMessage = nil

        do {
            let payload = try await APIClient.shared.loadAnalysisData(refresh: true)
            teams = payload.teams.sorted { $0.name < $1.name }

            if selectedHomeTeam.isEmpty {
                selectedHomeTeam = teams.first?.name ?? ""
            }
            if selectedAwayTeam.isEmpty {
                selectedAwayTeam = teams.dropFirst().first?.name ?? teams.first?.name ?? ""
            }
            if selectedAwayTeam == selectedHomeTeam, let alt = teams.first(where: { $0.name != selectedHomeTeam }) {
                selectedAwayTeam = alt.name
            }
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }

    var homeTeam: AnalysisTeam? {
        teams.first(where: { $0.name == selectedHomeTeam })
    }

    var awayTeam: AnalysisTeam? {
        teams.first(where: { $0.name == selectedAwayTeam })
    }

    func rank(of teamName: String, metric: RankingMetric) -> Int? {
        let sorted: [AnalysisTeam]
        switch metric {
        case .goalsScored:
            sorted = teams.sorted { ($0.stats.avgGoalsScored ?? -1) > ($1.stats.avgGoalsScored ?? -1) }
        case .goalsConceded:
            sorted = teams.sorted { ($0.stats.avgGoalsConceded ?? .greatestFiniteMagnitude) < ($1.stats.avgGoalsConceded ?? .greatestFiniteMagnitude) }
        case .winRate:
            sorted = teams.sorted { ($0.stats.winRate ?? -1) > ($1.stats.winRate ?? -1) }
        case .possession:
            sorted = teams.sorted { ($0.stats.avgPossession ?? -1) > ($1.stats.avgPossession ?? -1) }
        }

        guard let index = sorted.firstIndex(where: { $0.name == teamName }) else {
            return nil
        }
        return index + 1
    }
}

struct AnalysisView: View {
    @StateObject private var vm = AnalysisViewModel()

    var body: some View {
        NavigationStack {
            Form {
                Section("Team Comparison") {
                    Picker("Home", selection: $vm.selectedHomeTeam) {
                        ForEach(vm.teams) { team in
                            Text(team.name).tag(team.name)
                        }
                    }

                    Picker("Away", selection: $vm.selectedAwayTeam) {
                        ForEach(vm.teams) { team in
                            Text(team.name).tag(team.name)
                        }
                    }
                }

                if let home = vm.homeTeam, let away = vm.awayTeam {
                    Section("Key Metrics") {
                        MetricComparisonRow(
                            title: "Win Rate",
                            homeLabel: home.name,
                            awayLabel: away.name,
                            homeValue: home.stats.winRate,
                            awayValue: away.stats.winRate,
                            asPercent: true,
                            maxScale: 1
                        )
                        MetricComparisonRow(
                            title: "Goals Scored",
                            homeLabel: home.name,
                            awayLabel: away.name,
                            homeValue: home.stats.avgGoalsScored,
                            awayValue: away.stats.avgGoalsScored,
                            maxScale: 3.5
                        )
                        MetricComparisonRow(
                            title: "Goals Conceded",
                            homeLabel: home.name,
                            awayLabel: away.name,
                            homeValue: home.stats.avgGoalsConceded,
                            awayValue: away.stats.avgGoalsConceded,
                            maxScale: 3.5
                        )
                        MetricComparisonRow(
                            title: "Shots",
                            homeLabel: home.name,
                            awayLabel: away.name,
                            homeValue: home.stats.avgShots,
                            awayValue: away.stats.avgShots,
                            maxScale: 25
                        )
                        MetricComparisonRow(
                            title: "Possession",
                            homeLabel: home.name,
                            awayLabel: away.name,
                            homeValue: home.stats.avgPossession,
                            awayValue: away.stats.avgPossession,
                            asPercent: true,
                            maxScale: 1
                        )
                        MetricComparisonRow(
                            title: "Corners",
                            homeLabel: home.name,
                            awayLabel: away.name,
                            homeValue: home.stats.avgCorners,
                            awayValue: away.stats.avgCorners,
                            maxScale: 10
                        )
                    }

                    Section("Head-to-Head") {
                        if let h2h = home.headToHead[away.name] {
                            VStack(alignment: .leading, spacing: 8) {
                                HStack {
                                    Text(home.name)
                                    Spacer()
                                    Text("\(h2h.wins)W")
                                }
                                HStack {
                                    Text("Draws")
                                    Spacer()
                                    Text("\(h2h.draws)")
                                }
                                HStack {
                                    Text(away.name)
                                    Spacer()
                                    Text("\(h2h.losses)W")
                                }
                                HStack {
                                    Text("Goals")
                                    Spacer()
                                    Text("\(h2h.goalsFor) - \(h2h.goalsAgainst)")
                                }
                            }
                        } else {
                            Text("No head-to-head data available.")
                                .foregroundStyle(.secondary)
                        }
                    }

                    Section("Recent Form") {
                        FormRowBadgeView(teamName: home.name, results: home.recentForm)
                        FormRowBadgeView(teamName: away.name, results: away.recentForm)
                    }

                    Section("Goal Trend (Last 10)") {
                        GoalTrendChart(
                            homeTeam: home.name,
                            awayTeam: away.name,
                            homeHistory: home.matchHistory,
                            awayHistory: away.matchHistory
                        )
                    }

                    Section("Recent Matches") {
                        TeamRecentMatchesView(team: home)
                        TeamRecentMatchesView(team: away)
                    }

                    Section("League Rank") {
                        ForEach(AnalysisViewModel.RankingMetric.allCases) { metric in
                            HStack {
                                Text(metric.rawValue)
                                Spacer()
                                Text("#\(vm.rank(of: home.name, metric: metric) ?? 0)")
                                    .foregroundStyle(.blue)
                                Text("vs")
                                    .foregroundStyle(.secondary)
                                Text("#\(vm.rank(of: away.name, metric: metric) ?? 0)")
                                    .foregroundStyle(.red)
                            }
                            .font(.subheadline)
                        }
                    }
                }
            }
            .navigationTitle("Analysis")
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    Button("Refresh") {
                        Task { await vm.load() }
                    }
                    .disabled(vm.isLoading)
                }
            }
            .overlay {
                if vm.isLoading {
                    ProgressView("Loading analysis...")
                }
            }
            .task { await vm.load() }
            .refreshable {
                await vm.load()
            }
            .alert("Error", isPresented: .constant(vm.errorMessage != nil), presenting: vm.errorMessage) { _ in
                Button("OK") { vm.errorMessage = nil }
            } message: { message in
                Text(message)
            }
        }
    }
}

private struct MetricComparisonRow: View {
    let title: String
    let homeLabel: String
    let awayLabel: String
    let homeValue: Double?
    let awayValue: Double?
    var asPercent = false
    var maxScale: Double = 5

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.subheadline)
                .fontWeight(.semibold)

            HStack {
                Text(short(homeLabel))
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Spacer()
                Text(short(awayLabel))
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            HStack(spacing: 12) {
                statView(value: homeValue)
                statView(value: awayValue)
            }
        }
        .padding(.vertical, 4)
    }

    private func statView(value: Double?) -> some View {
        let normalized = max(min(value ?? 0, maxScale), 0)
        return VStack(alignment: .leading, spacing: 4) {
            ProgressView(value: normalized, total: maxScale)
            Text(formatted(value))
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func formatted(_ value: Double?) -> String {
        guard let value else { return "-" }
        if asPercent {
            return String(format: "%.1f%%", value * 100)
        }
        return String(format: "%.2f", value)
    }

    private func short(_ name: String) -> String {
        let maxChars = 12
        if name.count <= maxChars { return name }
        return String(name.prefix(maxChars)) + "…"
    }
}

private struct FormRowBadgeView: View {
    let teamName: String
    let results: [String]

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(teamName)
                .font(.subheadline)
                .fontWeight(.medium)
            HStack(spacing: 6) {
                ForEach(Array(results.enumerated()), id: \.offset) { _, item in
                    Text(item)
                        .font(.caption2)
                        .fontWeight(.bold)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 4)
                        .background(color(for: item).opacity(0.2), in: Capsule())
                        .foregroundStyle(color(for: item))
                }
            }
        }
    }

    private func color(for result: String) -> Color {
        switch result.uppercased() {
        case "W": return .green
        case "D": return .orange
        default: return .red
        }
    }
}

private struct TeamRecentMatchesView: View {
    let team: AnalysisTeam

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(team.name)
                .font(.subheadline)
                .fontWeight(.semibold)

            ForEach(team.matchHistory.prefix(4)) { item in
                HStack {
                    Text("\(item.homeAway) • \(item.opponent)")
                    Spacer()
                    Text("\(item.goalsFor)-\(item.goalsAgainst)")
                        .fontWeight(.medium)
                    Text(item.result)
                        .foregroundStyle(resultColor(item.result))
                        .fontWeight(.bold)
                }
                .font(.caption)
            }
        }
    }

    private func resultColor(_ value: String) -> Color {
        switch value.uppercased() {
        case "W": return .green
        case "D": return .orange
        default: return .red
        }
    }
}

#Preview {
    AnalysisView()
}
