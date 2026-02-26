import SwiftUI

@MainActor
final class SimulationViewModel: ObservableObject {
    private enum Keys {
        static let crossLeagueEnabled = "sim.crossLeagueEnabled"
        static let selectedLeague = "sim.selectedLeague"
        static let selectedHomeLeague = "sim.selectedHomeLeague"
        static let selectedAwayLeague = "sim.selectedAwayLeague"
        static let selectedHomeTeam = "sim.selectedHomeTeam"
        static let selectedAwayTeam = "sim.selectedAwayTeam"
        static let homeFormation = "sim.homeFormation"
        static let awayFormation = "sim.awayFormation"
        static let homeAdjustment = "sim.homeAdjustment"
        static let awayAdjustment = "sim.awayAdjustment"
    }

    private let defaults = UserDefaults.standard

    @Published var isLoading = false
    @Published var isRunning = false
    @Published var errorMessage: String?
    @Published var result: SimulationResponse?

    @Published var leagues: [SimulationLeague] = []
    @Published var crossLeagueEnabled = false { didSet { defaults.set(crossLeagueEnabled, forKey: Keys.crossLeagueEnabled) } }
    @Published var selectedLeague = "" { didSet { defaults.set(selectedLeague, forKey: Keys.selectedLeague) } }
    @Published var selectedHomeLeague = "" { didSet { defaults.set(selectedHomeLeague, forKey: Keys.selectedHomeLeague) } }
    @Published var selectedAwayLeague = "" { didSet { defaults.set(selectedAwayLeague, forKey: Keys.selectedAwayLeague) } }
    @Published var selectedHomeTeam = "" { didSet { defaults.set(selectedHomeTeam, forKey: Keys.selectedHomeTeam) } }
    @Published var selectedAwayTeam = "" { didSet { defaults.set(selectedAwayTeam, forKey: Keys.selectedAwayTeam) } }
    @Published var homeFormation = "4-2-3-1" { didSet { defaults.set(homeFormation, forKey: Keys.homeFormation) } }
    @Published var awayFormation = "4-2-3-1" { didSet { defaults.set(awayFormation, forKey: Keys.awayFormation) } }
    @Published var homeAdjustment: Double = 0 { didSet { defaults.set(homeAdjustment, forKey: Keys.homeAdjustment) } }
    @Published var awayAdjustment: Double = 0 { didSet { defaults.set(awayAdjustment, forKey: Keys.awayAdjustment) } }

    let formations: [String] = [
        "3-1-4-2", "3-2-4-1", "3-3-3-1", "3-4-1-2", "3-4-2-1", "3-4-3", "3-5-1-1", "3-5-2",
        "4-1-3-2", "4-1-4-1", "4-2-2-2", "4-2-3-1", "4-3-1-2", "4-3-3", "4-4-1-1", "4-4-2",
        "4-5-1", "5-3-2", "5-4-1"
    ]

    init() {
        crossLeagueEnabled = defaults.object(forKey: Keys.crossLeagueEnabled) as? Bool ?? false
        selectedLeague = defaults.string(forKey: Keys.selectedLeague) ?? ""
        selectedHomeLeague = defaults.string(forKey: Keys.selectedHomeLeague) ?? ""
        selectedAwayLeague = defaults.string(forKey: Keys.selectedAwayLeague) ?? ""
        selectedHomeTeam = defaults.string(forKey: Keys.selectedHomeTeam) ?? ""
        selectedAwayTeam = defaults.string(forKey: Keys.selectedAwayTeam) ?? ""
        homeFormation = defaults.string(forKey: Keys.homeFormation) ?? "4-2-3-1"
        awayFormation = defaults.string(forKey: Keys.awayFormation) ?? "4-2-3-1"
        homeAdjustment = defaults.object(forKey: Keys.homeAdjustment) as? Double ?? 0
        awayAdjustment = defaults.object(forKey: Keys.awayAdjustment) as? Double ?? 0
    }

    func loadIfNeeded() async {
        guard leagues.isEmpty else { return }
        await loadOptions()
    }

    func loadOptions() async {
        isLoading = true
        errorMessage = nil

        do {
            let payload = try await APIClient.shared.loadSimulationOptions()
            leagues = payload.leagues

            let defaultLeague = payload.defaultLeague ?? payload.leagues.first?.folder ?? ""
            if selectedLeague.isEmpty { selectedLeague = defaultLeague }
            syncLeagueMode()
            syncTeams()
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }

    func syncLeagueMode() {
        if !crossLeagueEnabled {
            selectedHomeLeague = selectedLeague
            selectedAwayLeague = selectedLeague
        } else {
            if selectedHomeLeague.isEmpty { selectedHomeLeague = selectedLeague }
            if selectedAwayLeague.isEmpty { selectedAwayLeague = selectedLeague }
        }
    }

    func syncTeams() {
        let homeSet = availableTeams(for: .home)
        let awaySet = availableTeams(for: .away)

        if !homeSet.contains(where: { $0.folder == selectedHomeTeam }) {
            selectedHomeTeam = homeSet.first?.folder ?? ""
        }
        if !awaySet.contains(where: { $0.folder == selectedAwayTeam }) {
            selectedAwayTeam = awaySet.first?.folder ?? ""
        }

        if selectedHomeTeam == selectedAwayTeam, awaySet.count > 1 {
            selectedAwayTeam = awaySet.first(where: { $0.folder != selectedHomeTeam })?.folder ?? selectedAwayTeam
        }
    }

    enum TeamSide {
        case home
        case away
    }

    func availableTeams(for side: TeamSide) -> [SimulationTeam] {
        let league = side == .home ? selectedHomeLeague : selectedAwayLeague
        return leagues.first(where: { $0.folder == league })?.teams ?? []
    }

    func runSimulation() async {
        guard !selectedHomeTeam.isEmpty, !selectedAwayTeam.isEmpty else {
            errorMessage = "Select both teams."
            return
        }

        isRunning = true
        errorMessage = nil
        result = nil

        do {
            let payload = SimulationRunRequest(
                league: selectedLeague,
                homeLeague: selectedHomeLeague,
                awayLeague: selectedAwayLeague,
                team1: selectedHomeTeam,
                team2: selectedAwayTeam,
                team1Formation: homeFormation,
                team2Formation: awayFormation,
                team1Adjustment: homeAdjustment,
                team2Adjustment: awayAdjustment,
                simulationCount: 60,
                includeHeatmaps: false,
                includeImages: false,
                includeMarkov: false
            )
            result = try await APIClient.shared.runSimulation(payload)
        } catch {
            errorMessage = error.localizedDescription
        }

        isRunning = false
    }
}

struct SimulationView: View {
    @StateObject private var vm = SimulationViewModel()

    var body: some View {
        NavigationStack {
            Form {
                Section("Setup") {
                    Toggle("Cross-League Match", isOn: $vm.crossLeagueEnabled)
                        .onChange(of: vm.crossLeagueEnabled) { _ in
                            vm.syncLeagueMode()
                            vm.syncTeams()
                        }

                    if vm.crossLeagueEnabled {
                        Picker("Home League", selection: $vm.selectedHomeLeague) {
                            ForEach(vm.leagues) { league in
                                Text(league.name).tag(league.folder)
                            }
                        }
                        .onChange(of: vm.selectedHomeLeague) { _ in vm.syncTeams() }

                        Picker("Away League", selection: $vm.selectedAwayLeague) {
                            ForEach(vm.leagues) { league in
                                Text(league.name).tag(league.folder)
                            }
                        }
                        .onChange(of: vm.selectedAwayLeague) { _ in vm.syncTeams() }
                    } else {
                        Picker("League", selection: $vm.selectedLeague) {
                            ForEach(vm.leagues) { league in
                                Text(league.name).tag(league.folder)
                            }
                        }
                        .onChange(of: vm.selectedLeague) { _ in
                            vm.syncLeagueMode()
                            vm.syncTeams()
                        }
                    }
                }

                Section("Teams") {
                    Picker("Home Team", selection: $vm.selectedHomeTeam) {
                        ForEach(vm.availableTeams(for: .home)) { team in
                            Text(team.name).tag(team.folder)
                        }
                    }

                    Picker("Away Team", selection: $vm.selectedAwayTeam) {
                        ForEach(vm.availableTeams(for: .away)) { team in
                            Text(team.name).tag(team.folder)
                        }
                    }
                }

                Section("Formations") {
                    Picker("Home Formation", selection: $vm.homeFormation) {
                        ForEach(vm.formations, id: \.self) { formation in
                            Text(formation).tag(formation)
                        }
                    }

                    Picker("Away Formation", selection: $vm.awayFormation) {
                        ForEach(vm.formations, id: \.self) { formation in
                            Text(formation).tag(formation)
                        }
                    }

                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: 12) {
                            FormationPitchView(
                                formation: vm.homeFormation,
                                teamName: vm.selectedHomeTeam.isEmpty ? "Home Team" : vm.selectedHomeTeam,
                                tint: .blue,
                                mirrorHorizontally: false
                            )
                            .frame(width: 200)

                            FormationPitchView(
                                formation: vm.awayFormation,
                                teamName: vm.selectedAwayTeam.isEmpty ? "Away Team" : vm.selectedAwayTeam,
                                tint: .red,
                                mirrorHorizontally: true
                            )
                            .frame(width: 200)
                        }
                        .padding(.vertical, 4)
                    }
                }

                Section("Adjustments") {
                    VStack(alignment: .leading, spacing: 8) {
                        HStack {
                            Text("Home")
                            Spacer()
                            Text(String(format: "%+.1f", vm.homeAdjustment))
                                .foregroundStyle(.secondary)
                        }
                        Slider(value: $vm.homeAdjustment, in: -10...10, step: 0.1)
                    }

                    VStack(alignment: .leading, spacing: 8) {
                        HStack {
                            Text("Away")
                            Spacer()
                            Text(String(format: "%+.1f", vm.awayAdjustment))
                                .foregroundStyle(.secondary)
                        }
                        Slider(value: $vm.awayAdjustment, in: -10...10, step: 0.1)
                    }
                }

                Section {
                    Button {
                        Task { await vm.runSimulation() }
                    } label: {
                        if vm.isRunning {
                            HStack {
                                ProgressView()
                                Text("Running...")
                            }
                        } else {
                            Text("Run Prediction")
                        }
                    }
                    .disabled(vm.isRunning || vm.selectedHomeTeam.isEmpty || vm.selectedAwayTeam.isEmpty)
                }

                if let result = vm.result {
                    Section("Result") {
                        TeamLogoRow(
                            homeName: result.team1 ?? vm.selectedHomeTeam,
                            awayName: result.team2 ?? vm.selectedAwayTeam,
                            homeLogoURL: fullURL(result.homeLogoURL),
                            awayLogoURL: fullURL(result.awayLogoURL)
                        )

                        LabeledContent("Predicted Score", value: result.predictedScore ?? "-")
                        LabeledContent("Expected Goals", value: "\(formatDecimal(result.expectedHomeGoals)) - \(formatDecimal(result.expectedAwayGoals))")
                        if let count = result.simulatedMatches {
                            LabeledContent("Simulations", value: "\(count)")
                        }
                    }

                    Section("Probabilities") {
                        OutcomeProbabilityChart(
                            home: result.winProbability ?? 0,
                            draw: result.drawProbability ?? 0,
                            away: result.loseProbability ?? 0
                        )
                        ProbabilityBar(title: "Home Win", value: result.winProbability ?? 0, tint: .blue)
                        ProbabilityBar(title: "Draw", value: result.drawProbability ?? 0, tint: .orange)
                        ProbabilityBar(title: "Away Win", value: result.loseProbability ?? 0, tint: .red)
                    }

                    let homePerspective = result.topScorelinesHomePerspective.isEmpty ? result.topScorelines : result.topScorelinesHomePerspective
                    if !homePerspective.isEmpty {
                        Section("Top Scorelines (Home Perspective)") {
                            ForEach(homePerspective.prefix(5)) { row in
                                ScorelineBarRow(score: row.score, percentage: row.percentage)
                            }
                        }
                    }

                    if !result.topScorelinesAwayPerspective.isEmpty {
                        Section("Top Scorelines (Away Perspective)") {
                            ForEach(result.topScorelinesAwayPerspective.prefix(5)) { row in
                                ScorelineBarRow(score: row.score, percentage: row.percentage)
                            }
                        }
                    }

                    if let adjustments = result.adjustments {
                        Section("Applied Adjustments") {
                            LabeledContent("Home Final", value: signed(adjustments.team1))
                            LabeledContent("Away Final", value: signed(adjustments.team2))
                            LabeledContent("Home Manual", value: signed(adjustments.manualTeam1))
                            LabeledContent("Away Manual", value: signed(adjustments.manualTeam2))
                            LabeledContent("Home HMM", value: signed(adjustments.hmmTeam1))
                            LabeledContent("Away HMM", value: signed(adjustments.hmmTeam2))
                            LabeledContent("HMM Applied", value: (adjustments.hmmApplied ?? false) ? "Yes" : "No")
                        }
                    }
                }
            }
            .navigationTitle("Simulation")
            .overlay {
                if vm.isLoading {
                    ProgressView("Loading leagues...")
                }
            }
            .task {
                await vm.loadIfNeeded()
            }
            .refreshable {
                await vm.loadOptions()
            }
            .alert("Error", isPresented: .constant(vm.errorMessage != nil), presenting: vm.errorMessage) { _ in
                Button("OK") { vm.errorMessage = nil }
            } message: { message in
                Text(message)
            }
        }
    }

    private func formatDecimal(_ value: Double?) -> String {
        guard let value else { return "-" }
        return String(format: "%.2f", value)
    }

    private func signed(_ value: Double?) -> String {
        guard let value else { return "-" }
        return String(format: "%+.2f%%", value)
    }

    private func fullURL(_ rawValue: String?) -> URL? {
        guard let rawValue, !rawValue.isEmpty else { return nil }
        if rawValue.hasPrefix("http://") || rawValue.hasPrefix("https://") {
            return URL(string: rawValue)
        }
        let base = AppConfig.apiBaseURL.absoluteString.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        return URL(string: "\(base)/\(rawValue.trimmingCharacters(in: CharacterSet(charactersIn: "/")))")
    }
}

private struct TeamLogoRow: View {
    let homeName: String
    let awayName: String
    let homeLogoURL: URL?
    let awayLogoURL: URL?

    var body: some View {
        HStack(spacing: 24) {
            TeamLogoView(name: homeName, url: homeLogoURL)
            TeamLogoView(name: awayName, url: awayLogoURL)
        }
        .frame(maxWidth: .infinity)
    }
}

private struct TeamLogoView: View {
    let name: String
    let url: URL?

    var body: some View {
        VStack(spacing: 8) {
            if let url {
                AsyncImage(url: url) { phase in
                    switch phase {
                    case .empty:
                        ProgressView()
                            .frame(width: 56, height: 56)
                    case .success(let image):
                        image
                            .resizable()
                            .scaledToFit()
                            .frame(width: 56, height: 56)
                    case .failure:
                        Image(systemName: "shield")
                            .font(.title2)
                            .foregroundStyle(.secondary)
                            .frame(width: 56, height: 56)
                    @unknown default:
                        EmptyView()
                    }
                }
            } else {
                Image(systemName: "shield")
                    .font(.title2)
                    .foregroundStyle(.secondary)
                    .frame(width: 56, height: 56)
            }
            Text(name)
                .font(.caption)
                .lineLimit(1)
        }
    }
}

private struct ProbabilityBar: View {
    let title: String
    let value: Double
    let tint: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(title)
                Spacer()
                Text(String(format: "%.1f%%", value))
                    .foregroundStyle(.secondary)
            }
            ProgressView(value: max(min(value, 100), 0), total: 100)
                .tint(tint)
        }
    }
}

private struct ScorelineBarRow: View {
    let score: String
    let percentage: Double

    var body: some View {
        HStack(spacing: 10) {
            Text(score)
                .fontWeight(.medium)
                .frame(width: 52, alignment: .leading)

            GeometryReader { geometry in
                let width = max(min(percentage, 100), 0) / 100 * geometry.size.width
                ZStack(alignment: .leading) {
                    Capsule().fill(Color.secondary.opacity(0.15))
                    Capsule().fill(Color.accentColor).frame(width: width)
                }
            }
            .frame(height: 10)

            Text(String(format: "%.1f%%", percentage))
                .font(.caption)
                .foregroundStyle(.secondary)
                .frame(width: 48, alignment: .trailing)
        }
        .frame(height: 22)
    }
}

#Preview {
    SimulationView()
}
