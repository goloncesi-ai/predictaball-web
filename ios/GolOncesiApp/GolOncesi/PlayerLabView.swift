import SwiftUI

@MainActor
final class PlayerLabViewModel: ObservableObject {
    private enum Keys {
        static let selectedTeam = "playerLab.selectedTeam"
        static let compareMode = "playerLab.compareMode"
        static let selectedPlayerA = "playerLab.selectedPlayerA"
        static let selectedPlayerB = "playerLab.selectedPlayerB"
    }

    private let defaults = UserDefaults.standard

    @Published var isLoading = false
    @Published var errorMessage: String?

    @Published var teams: [PlayerAnalysisTeam] = []
    @Published var players: [PlayerProfile] = []

    @Published var selectedTeam = "All Teams" { didSet { defaults.set(selectedTeam, forKey: Keys.selectedTeam) } }
    @Published var compareMode = false { didSet { defaults.set(compareMode, forKey: Keys.compareMode) } }
    @Published var selectedPlayerA = "" { didSet { defaults.set(selectedPlayerA, forKey: Keys.selectedPlayerA) } }
    @Published var selectedPlayerB = "" { didSet { defaults.set(selectedPlayerB, forKey: Keys.selectedPlayerB) } }

    private let preferredMetricOrder: [String] = [
        "Rating", "Appearances", "Goals", "Assists", "MinutesPlayed",
        "Expected goals (xG)", "Expected assists (xA)", "Shots on target per game", "Key passes"
    ]

    init() {
        selectedTeam = defaults.string(forKey: Keys.selectedTeam) ?? "All Teams"
        compareMode = defaults.object(forKey: Keys.compareMode) as? Bool ?? false
        selectedPlayerA = defaults.string(forKey: Keys.selectedPlayerA) ?? ""
        selectedPlayerB = defaults.string(forKey: Keys.selectedPlayerB) ?? ""
    }

    func load() async {
        isLoading = true
        errorMessage = nil

        do {
            let payload = try await APIClient.shared.loadPlayerAnalysis(limit: 2)
            teams = payload.teams.sorted { $0.name < $1.name }
            players = payload.players.sorted {
                if $0.team == $1.team {
                    return $0.name < $1.name
                }
                return $0.team < $1.team
            }

            if selectedPlayerA.isEmpty {
                selectedPlayerA = filteredPlayers.first?.id ?? ""
            }
            if selectedPlayerB.isEmpty {
                selectedPlayerB = filteredPlayers.dropFirst().first?.id ?? ""
            }
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }

    var teamFilters: [String] {
        ["All Teams"] + teams.map { $0.name }
    }

    var filteredPlayers: [PlayerProfile] {
        if selectedTeam == "All Teams" {
            return players
        }
        return players.filter { $0.team == selectedTeam }
    }

    func syncSelectionsAfterFilterChange() {
        let validIDs = Set(filteredPlayers.map { $0.id })
        if !validIDs.contains(selectedPlayerA) {
            selectedPlayerA = filteredPlayers.first?.id ?? ""
        }
        if !validIDs.contains(selectedPlayerB) {
            selectedPlayerB = filteredPlayers.dropFirst().first?.id ?? ""
        }
    }

    var playerA: PlayerProfile? {
        players.first(where: { $0.id == selectedPlayerA })
    }

    var playerB: PlayerProfile? {
        guard compareMode else { return nil }
        return players.first(where: { $0.id == selectedPlayerB })
    }

    func displayValue(for key: String, in player: PlayerProfile) -> String {
        if let value = player.seasonSummary?.metrics[key]?.asString {
            return value
        }
        if let value = player.detailedStats?.metrics[key]?.asString {
            return value
        }
        return "-"
    }

    func numericValue(for key: String, in player: PlayerProfile) -> Double? {
        player.seasonSummary?.metrics[key]?.asDouble ?? player.detailedStats?.metrics[key]?.asDouble
    }

    func comparisonMetrics(playerA: PlayerProfile, playerB: PlayerProfile?) -> [String] {
        guard let playerB else {
            return preferredMetricOrder.filter { displayValue(for: $0, in: playerA) != "-" }
        }

        let keysA: Set<String> = (playerA.seasonSummary.map { Set($0.metrics.keys) } ?? [])
            .union(playerA.detailedStats.map { Set($0.metrics.keys) } ?? [])
        let keysB: Set<String> = (playerB.seasonSummary.map { Set($0.metrics.keys) } ?? [])
            .union(playerB.detailedStats.map { Set($0.metrics.keys) } ?? [])

        let intersection = keysA.intersection(keysB)
        let orderedPreferred = preferredMetricOrder.filter { intersection.contains($0) }
        let extra = intersection.subtracting(Set(preferredMetricOrder)).sorted()
        return orderedPreferred + Array(extra.prefix(6))
    }

    func comparisonChartRows(playerA: PlayerProfile, playerB: PlayerProfile) -> [PlayerComparisonChart.MetricRow] {
        let metrics = comparisonMetrics(playerA: playerA, playerB: playerB)
        let numericRows = metrics.compactMap { key -> PlayerComparisonChart.MetricRow? in
            guard let a = numericValue(for: key, in: playerA),
                  let b = numericValue(for: key, in: playerB) else {
                return nil
            }
            return PlayerComparisonChart.MetricRow(metric: key, valueA: a, valueB: b)
        }
        return Array(numericRows.prefix(6))
    }
}

struct PlayerLabView: View {
    @StateObject private var vm = PlayerLabViewModel()

    var body: some View {
        NavigationStack {
            Form {
                Section("Filters") {
                    Picker("Team", selection: $vm.selectedTeam) {
                        ForEach(vm.teamFilters, id: \.self) { team in
                            Text(team).tag(team)
                        }
                    }
                    .onChange(of: vm.selectedTeam) { _ in
                        vm.syncSelectionsAfterFilterChange()
                    }

                    Toggle("Compare Mode", isOn: $vm.compareMode)
                }

                Section("Players") {
                    Picker("Player A", selection: $vm.selectedPlayerA) {
                        ForEach(vm.filteredPlayers) { player in
                            Text("\(player.name) (\(player.team))").tag(player.id)
                        }
                    }

                    if vm.compareMode {
                        Picker("Player B", selection: $vm.selectedPlayerB) {
                            ForEach(vm.filteredPlayers) { player in
                                Text("\(player.name) (\(player.team))").tag(player.id)
                            }
                        }
                    }
                }

                if let playerA = vm.playerA {
                    if let playerB = vm.playerB {
                        Section("Comparison") {
                            CompareHeaderView(playerA: playerA, playerB: playerB)

                            let chartRows = vm.comparisonChartRows(playerA: playerA, playerB: playerB)
                            if !chartRows.isEmpty {
                                PlayerComparisonChart(
                                    playerAName: playerA.name,
                                    playerBName: playerB.name,
                                    rows: chartRows
                                )
                            }

                            let metrics = vm.comparisonMetrics(playerA: playerA, playerB: playerB)
                            ForEach(metrics, id: \.self) { key in
                                MetricCompareRow(
                                    title: key,
                                    valueA: vm.displayValue(for: key, in: playerA),
                                    valueB: vm.displayValue(for: key, in: playerB),
                                    numericA: vm.numericValue(for: key, in: playerA),
                                    numericB: vm.numericValue(for: key, in: playerB)
                                )
                            }
                        }
                    } else {
                        Section("Profile") {
                            PlayerMetricView(player: playerA, metrics: vm.comparisonMetrics(playerA: playerA, playerB: nil), valueResolver: vm.displayValue(for:in:))
                        }
                    }
                }
            }
            .navigationTitle("Player Lab")
            .overlay {
                if vm.isLoading {
                    ProgressView("Loading players...")
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

private struct CompareHeaderView: View {
    let playerA: PlayerProfile
    let playerB: PlayerProfile

    var body: some View {
        HStack(spacing: 12) {
            VStack(alignment: .leading) {
                Text(playerA.name)
                    .font(.subheadline)
                    .fontWeight(.semibold)
                Text(playerA.team)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            Image(systemName: "arrow.left.and.right")
                .foregroundStyle(.secondary)
            Spacer()
            VStack(alignment: .trailing) {
                Text(playerB.name)
                    .font(.subheadline)
                    .fontWeight(.semibold)
                Text(playerB.team)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
    }
}

private struct MetricCompareRow: View {
    let title: String
    let valueA: String
    let valueB: String
    let numericA: Double?
    let numericB: Double?

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title)
                .font(.caption)
                .foregroundStyle(.secondary)

            HStack {
                Text(valueA)
                    .frame(maxWidth: .infinity, alignment: .leading)
                deltaView
                Text(valueB)
                    .frame(maxWidth: .infinity, alignment: .trailing)
            }
            .font(.subheadline)
        }
        .padding(.vertical, 3)
    }

    @ViewBuilder
    private var deltaView: some View {
        if let a = numericA, let b = numericB {
            let delta = a - b
            Text(String(format: "%+.2f", delta))
                .font(.caption)
                .fontWeight(.semibold)
                .foregroundStyle(deltaColor(delta))
                .frame(minWidth: 58, alignment: .center)
        } else {
            Text("-")
                .font(.caption)
                .foregroundStyle(.secondary)
                .frame(minWidth: 58, alignment: .center)
        }
    }

    private func deltaColor(_ value: Double) -> Color {
        if value > 0 { return .green }
        if value < 0 { return .red }
        return .secondary
    }
}

private struct PlayerMetricView: View {
    let player: PlayerProfile
    let metrics: [String]
    let valueResolver: (String, PlayerProfile) -> String

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(player.name)
                .font(.headline)
            Text(player.team)
                .font(.subheadline)
                .foregroundStyle(.secondary)

            ForEach(metrics, id: \.self) { key in
                LabeledContent(key, value: valueResolver(key, player))
            }
        }
        .padding(.vertical, 4)
    }
}

#Preview {
    PlayerLabView()
}
