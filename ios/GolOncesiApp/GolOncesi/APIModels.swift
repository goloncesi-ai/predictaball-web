import Foundation

struct SimulationOptionsResponse: Decodable {
    let defaultLeague: String?
    let leagues: [SimulationLeague]

    enum CodingKeys: String, CodingKey {
        case defaultLeague = "default_league"
        case leagues
    }
}

struct SimulationLeague: Decodable, Hashable, Identifiable {
    let name: String
    let folder: String
    let teamCount: Int?
    let teams: [SimulationTeam]

    var id: String { folder }

    enum CodingKeys: String, CodingKey {
        case name
        case folder
        case teamCount = "team_count"
        case teams
    }
}

struct SimulationTeam: Decodable, Hashable, Identifiable {
    let name: String
    let folder: String
    let lineupCSVPath: String?

    var id: String { folder }

    enum CodingKeys: String, CodingKey {
        case name
        case folder
        case lineupCSVPath = "lineup_csv_path"
    }
}

struct SimulationRunRequest: Encodable {
    let league: String
    let homeLeague: String
    let awayLeague: String
    let team1: String
    let team2: String
    let team1Formation: String?
    let team2Formation: String?
    let team1Adjustment: Double
    let team2Adjustment: Double
    let simulationCount: Int
    let includeHeatmaps: Bool
    let includeImages: Bool
    let includeMarkov: Bool

    enum CodingKeys: String, CodingKey {
        case league
        case homeLeague = "home_league"
        case awayLeague = "away_league"
        case team1
        case team2
        case team1Formation = "team1_formation"
        case team2Formation = "team2_formation"
        case team1Adjustment = "team1_adj"
        case team2Adjustment = "team2_adj"
        case simulationCount = "simulation_count"
        case includeHeatmaps = "include_heatmaps"
        case includeImages = "include_images"
        case includeMarkov = "include_markov"
    }
}

struct SimulationResponse: Decodable {
    let team1: String?
    let team2: String?
    let league: String?
    let homeLeague: String?
    let awayLeague: String?
    let crossLeague: Bool?
    let predictedScore: String?
    let expectedHomeGoals: Double?
    let expectedAwayGoals: Double?
    let winProbability: Double?
    let drawProbability: Double?
    let loseProbability: Double?
    let simulatedMatches: Int?
    let homeLogoURL: String?
    let awayLogoURL: String?
    let topScorelines: [ScorelineProbability]
    let topScorelinesHomePerspective: [ScorelineProbability]
    let topScorelinesAwayPerspective: [ScorelineProbability]
    let adjustments: SimulationAdjustments?

    enum CodingKeys: String, CodingKey {
        case team1
        case team2
        case league
        case homeLeague = "home_league"
        case awayLeague = "away_league"
        case crossLeague = "cross_league"
        case predictedScore = "predicted_score"
        case expectedHomeGoals = "exp_home_goals"
        case expectedAwayGoals = "exp_away_goals"
        case winProbability = "win_prob"
        case drawProbability = "draw_prob"
        case loseProbability = "lose_prob"
        case simulatedMatches = "simulated_matches"
        case homeLogoURL = "team1_logo_url"
        case awayLogoURL = "team2_logo_url"
        case topScorelines = "top5_scores"
        case topScorelinesHomePerspective = "top5_scores_home_perspective"
        case topScorelinesAwayPerspective = "top5_scores_away_perspective"
        case probabilities
        case expectedGoals = "expected_goals"
        case adjustments
    }

    struct LegacyProbabilities: Decodable {
        let homeWin: Double?
        let draw: Double?
        let awayWin: Double?

        enum CodingKeys: String, CodingKey {
            case homeWin = "home_win"
            case draw
            case awayWin = "away_win"
        }

        init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self)
            homeWin = c.decodeLossyDoubleIfPresent(forKey: .homeWin)
            draw = c.decodeLossyDoubleIfPresent(forKey: .draw)
            awayWin = c.decodeLossyDoubleIfPresent(forKey: .awayWin)
        }
    }

    struct LegacyExpectedGoals: Decodable {
        let home: Double?
        let away: Double?

        init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: DynamicCodingKey.self)
            home = c.decodeLossyDoubleIfPresent(forKey: DynamicCodingKey("home"))
            away = c.decodeLossyDoubleIfPresent(forKey: DynamicCodingKey("away"))
        }
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        team1 = try c.decodeIfPresent(String.self, forKey: .team1)
        team2 = try c.decodeIfPresent(String.self, forKey: .team2)
        league = try c.decodeIfPresent(String.self, forKey: .league)
        homeLeague = try c.decodeIfPresent(String.self, forKey: .homeLeague)
        awayLeague = try c.decodeIfPresent(String.self, forKey: .awayLeague)
        crossLeague = try c.decodeIfPresent(Bool.self, forKey: .crossLeague)
        predictedScore = try c.decodeIfPresent(String.self, forKey: .predictedScore)

        let legacyExpectedGoals = try c.decodeIfPresent(LegacyExpectedGoals.self, forKey: .expectedGoals)
        expectedHomeGoals = c.decodeLossyDoubleIfPresent(forKey: .expectedHomeGoals) ?? legacyExpectedGoals?.home
        expectedAwayGoals = c.decodeLossyDoubleIfPresent(forKey: .expectedAwayGoals) ?? legacyExpectedGoals?.away

        let legacyProbabilities = try c.decodeIfPresent(LegacyProbabilities.self, forKey: .probabilities)
        winProbability = c.decodeLossyDoubleIfPresent(forKey: .winProbability) ?? legacyProbabilities?.homeWin
        drawProbability = c.decodeLossyDoubleIfPresent(forKey: .drawProbability) ?? legacyProbabilities?.draw
        loseProbability = c.decodeLossyDoubleIfPresent(forKey: .loseProbability) ?? legacyProbabilities?.awayWin

        simulatedMatches = c.decodeLossyIntIfPresent(forKey: .simulatedMatches)
        homeLogoURL = try c.decodeIfPresent(String.self, forKey: .homeLogoURL)
        awayLogoURL = try c.decodeIfPresent(String.self, forKey: .awayLogoURL)
        topScorelines = (try? c.decode([ScorelineProbability].self, forKey: .topScorelines)) ?? []
        topScorelinesHomePerspective = (try? c.decode([ScorelineProbability].self, forKey: .topScorelinesHomePerspective)) ?? []
        topScorelinesAwayPerspective = (try? c.decode([ScorelineProbability].self, forKey: .topScorelinesAwayPerspective)) ?? []
        adjustments = try c.decodeIfPresent(SimulationAdjustments.self, forKey: .adjustments)
    }
}

struct SimulationAdjustments: Decodable {
    let team1: Double?
    let team2: Double?
    let manualTeam1: Double?
    let manualTeam2: Double?
    let hmmTeam1: Double?
    let hmmTeam2: Double?
    let hmmApplied: Bool?

    enum CodingKeys: String, CodingKey {
        case team1
        case team2
        case manualTeam1 = "manual_team1"
        case manualTeam2 = "manual_team2"
        case hmmTeam1 = "hmm_team1"
        case hmmTeam2 = "hmm_team2"
        case hmmApplied = "hmm_applied"
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        team1 = c.decodeLossyDoubleIfPresent(forKey: .team1)
        team2 = c.decodeLossyDoubleIfPresent(forKey: .team2)
        manualTeam1 = c.decodeLossyDoubleIfPresent(forKey: .manualTeam1)
        manualTeam2 = c.decodeLossyDoubleIfPresent(forKey: .manualTeam2)
        hmmTeam1 = c.decodeLossyDoubleIfPresent(forKey: .hmmTeam1)
        hmmTeam2 = c.decodeLossyDoubleIfPresent(forKey: .hmmTeam2)
        hmmApplied = try c.decodeIfPresent(Bool.self, forKey: .hmmApplied)
    }
}

struct ScorelineProbability: Decodable, Identifiable {
    let score: String
    let percentage: Double

    var id: String { "\(score)-\(percentage)" }

    enum CodingKeys: String, CodingKey {
        case score
        case percentage
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        score = (try? c.decode(String.self, forKey: .score)) ?? "-"
        percentage = c.decodeLossyDoubleIfPresent(forKey: .percentage) ?? 0
    }
}

struct CurrentRoundResponse: Decodable {
    let currentRound: Int

    enum CodingKeys: String, CodingKey {
        case currentRound = "current_round"
    }
}

struct RecentGamesResponse: Decodable {
    let round: Int
    let matches: [RecentGame]
}

struct RecentGame: Decodable, Identifiable {
    let matchID: String
    let date: String?
    let time: String?
    let homeTeam: String
    let awayTeam: String
    let status: String?
    let actualScore: String?
    let prediction: RecentGamePrediction?

    var id: String { matchID }

    enum CodingKeys: String, CodingKey {
        case matchID = "match_id"
        case date
        case time
        case homeTeam = "home_team"
        case awayTeam = "away_team"
        case status
        case actualScore = "actual_score"
        case prediction
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        if let strID = try? c.decode(String.self, forKey: .matchID) {
            matchID = strID
        } else if let intID = try? c.decode(Int.self, forKey: .matchID) {
            matchID = String(intID)
        } else {
            matchID = UUID().uuidString
        }

        date = try c.decodeIfPresent(String.self, forKey: .date)
        time = try c.decodeIfPresent(String.self, forKey: .time)
        homeTeam = (try? c.decode(String.self, forKey: .homeTeam)) ?? "Home"
        awayTeam = (try? c.decode(String.self, forKey: .awayTeam)) ?? "Away"
        status = try c.decodeIfPresent(String.self, forKey: .status)
        actualScore = try c.decodeIfPresent(String.self, forKey: .actualScore)
        prediction = try c.decodeIfPresent(RecentGamePrediction.self, forKey: .prediction)
    }
}

struct RecentGamePrediction: Decodable {
    let predictedScore: String?
    let confidence: String?
    let probabilities: RecentPredictionProbabilities?
    let expectedGoals: RecentExpectedGoals?
    let topScorelines: [ScorelineProbability]
    let topScorelinesHomePerspective: [ScorelineProbability]
    let topScorelinesAwayPerspective: [ScorelineProbability]

    enum CodingKeys: String, CodingKey {
        case predictedScore = "predicted_score"
        case confidence
        case probabilities
        case expectedGoals = "expected_goals"
        case topScorelines = "top5_scores"
        case topScorelinesHomePerspective = "top5_scores_home_perspective"
        case topScorelinesAwayPerspective = "top5_scores_away_perspective"
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        predictedScore = try c.decodeIfPresent(String.self, forKey: .predictedScore)
        confidence = try c.decodeIfPresent(String.self, forKey: .confidence)
        probabilities = try c.decodeIfPresent(RecentPredictionProbabilities.self, forKey: .probabilities)
        expectedGoals = try c.decodeIfPresent(RecentExpectedGoals.self, forKey: .expectedGoals)
        topScorelines = (try? c.decode([ScorelineProbability].self, forKey: .topScorelines)) ?? []
        topScorelinesHomePerspective = (try? c.decode([ScorelineProbability].self, forKey: .topScorelinesHomePerspective)) ?? topScorelines
        topScorelinesAwayPerspective = (try? c.decode([ScorelineProbability].self, forKey: .topScorelinesAwayPerspective)) ?? []
    }
}

struct RecentPredictionProbabilities: Decodable {
    let homeWin: Double?
    let draw: Double?
    let awayWin: Double?

    enum CodingKeys: String, CodingKey {
        case homeWin = "home_win"
        case draw
        case awayWin = "away_win"
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        homeWin = c.decodeLossyDoubleIfPresent(forKey: .homeWin)
        draw = c.decodeLossyDoubleIfPresent(forKey: .draw)
        awayWin = c.decodeLossyDoubleIfPresent(forKey: .awayWin)
    }
}

struct RecentExpectedGoals: Decodable {
    let home: Double?
    let away: Double?

    init(from decoder: Decoder) throws {
        let c = try decoder.singleValueContainer()
        if let dict = try? c.decode([String: Double].self) {
            home = dict["home"]
            away = dict["away"]
        } else if let dict = try? c.decode([String: Int].self) {
            home = dict["home"].map(Double.init)
            away = dict["away"].map(Double.init)
        } else {
            home = nil
            away = nil
        }
    }
}

struct AnalysisDataResponse: Decodable {
    let teams: [AnalysisTeam]
}

struct AnalysisTeam: Decodable, Identifiable {
    let name: String
    let stats: TeamStats
    let matchHistory: [TeamMatchHistory]
    let headToHead: [String: HeadToHeadStats]

    var id: String { name }

    enum CodingKeys: String, CodingKey {
        case name
        case stats
        case matchHistory = "match_history"
        case headToHead = "head_to_head"
    }

    var recentForm: [String] {
        Array(matchHistory.prefix(10)).map { $0.result }
    }
}

struct TeamStats: Decodable {
    let winRate: Double?
    let avgGoalsScored: Double?
    let avgGoalsConceded: Double?
    let avgShots: Double?
    let avgPossession: Double?
    let avgCorners: Double?
    let totalGames: Int?
    let wins: Int?
    let draws: Int?
    let losses: Int?

    enum CodingKeys: String, CodingKey {
        case winRate = "win_rate"
        case avgGoalsScored = "avg_goals_scored"
        case avgGoalsConceded = "avg_goals_conceded"
        case avgShots = "avg_shots"
        case avgPossession = "avg_possession"
        case avgCorners = "avg_corners"
        case totalGames = "total_games"
        case wins
        case draws
        case losses
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        winRate = c.decodeLossyDoubleIfPresent(forKey: .winRate)
        avgGoalsScored = c.decodeLossyDoubleIfPresent(forKey: .avgGoalsScored)
        avgGoalsConceded = c.decodeLossyDoubleIfPresent(forKey: .avgGoalsConceded)
        avgShots = c.decodeLossyDoubleIfPresent(forKey: .avgShots)
        avgPossession = c.decodeLossyDoubleIfPresent(forKey: .avgPossession)
        avgCorners = c.decodeLossyDoubleIfPresent(forKey: .avgCorners)
        totalGames = c.decodeLossyIntIfPresent(forKey: .totalGames)
        wins = c.decodeLossyIntIfPresent(forKey: .wins)
        draws = c.decodeLossyIntIfPresent(forKey: .draws)
        losses = c.decodeLossyIntIfPresent(forKey: .losses)
    }
}

struct TeamMatchHistory: Decodable, Identifiable {
    let opponent: String
    let homeAway: String
    let goalsFor: Int
    let goalsAgainst: Int
    let shots: Int
    let possession: Double
    let corners: Int
    let passes: Int
    let bigChances: Int
    let result: String

    var id: String {
        "\(opponent)-\(goalsFor)-\(goalsAgainst)-\(homeAway)"
    }

    enum CodingKeys: String, CodingKey {
        case opponent
        case homeAway = "home_away"
        case goalsFor = "goals_for"
        case goalsAgainst = "goals_against"
        case shots
        case possession
        case corners
        case passes
        case bigChances = "big_chances"
        case result
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        opponent = (try? c.decode(String.self, forKey: .opponent)) ?? "-"
        homeAway = (try? c.decode(String.self, forKey: .homeAway)) ?? "-"
        goalsFor = c.decodeLossyIntIfPresent(forKey: .goalsFor) ?? 0
        goalsAgainst = c.decodeLossyIntIfPresent(forKey: .goalsAgainst) ?? 0
        shots = c.decodeLossyIntIfPresent(forKey: .shots) ?? 0
        possession = c.decodeLossyDoubleIfPresent(forKey: .possession) ?? 0
        corners = c.decodeLossyIntIfPresent(forKey: .corners) ?? 0
        passes = c.decodeLossyIntIfPresent(forKey: .passes) ?? 0
        bigChances = c.decodeLossyIntIfPresent(forKey: .bigChances) ?? 0
        result = (try? c.decode(String.self, forKey: .result)) ?? "-"
    }
}

struct HeadToHeadStats: Decodable {
    let wins: Int
    let draws: Int
    let losses: Int
    let goalsFor: Int
    let goalsAgainst: Int

    enum CodingKeys: String, CodingKey {
        case wins
        case draws
        case losses
        case goalsFor = "goals_for"
        case goalsAgainst = "goals_against"
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        wins = c.decodeLossyIntIfPresent(forKey: .wins) ?? 0
        draws = c.decodeLossyIntIfPresent(forKey: .draws) ?? 0
        losses = c.decodeLossyIntIfPresent(forKey: .losses) ?? 0
        goalsFor = c.decodeLossyIntIfPresent(forKey: .goalsFor) ?? 0
        goalsAgainst = c.decodeLossyIntIfPresent(forKey: .goalsAgainst) ?? 0
    }
}

struct PlayerAnalysisResponse: Decodable {
    let teams: [PlayerAnalysisTeam]
    let players: [PlayerProfile]
}

struct PlayerAnalysisTeam: Decodable, Identifiable {
    let name: String
    let playerCount: Int?

    var id: String { name }

    enum CodingKeys: String, CodingKey {
        case name
        case playerCount = "playerCount"
    }
}

struct PlayerProfile: Decodable, Identifiable {
    let id: String
    let name: String
    let team: String
    let seasonSummary: PlayerSeasonSummary?
    let detailedStats: PlayerDetailedStats?

    enum CodingKeys: String, CodingKey {
        case id
        case name
        case team
        case seasonSummary
        case detailedStats
    }
}

struct PlayerSeasonSummary: Decodable {
    let metrics: [String: JSONValue]
}

struct PlayerDetailedStats: Decodable {
    let metrics: [String: JSONValue]
}

enum JSONValue: Decodable {
    case string(String)
    case int(Int)
    case double(Double)
    case bool(Bool)
    case null

    init(from decoder: Decoder) throws {
        let c = try decoder.singleValueContainer()
        if c.decodeNil() {
            self = .null
        } else if let value = try? c.decode(Bool.self) {
            self = .bool(value)
        } else if let value = try? c.decode(Int.self) {
            self = .int(value)
        } else if let value = try? c.decode(Double.self) {
            self = .double(value)
        } else if let value = try? c.decode(String.self) {
            self = .string(value)
        } else {
            self = .null
        }
    }

    var asDouble: Double? {
        switch self {
        case .double(let v): return v
        case .int(let v): return Double(v)
        case .string(let v):
            let clean = v
                .replacingOccurrences(of: "%", with: "")
                .replacingOccurrences(of: ",", with: ".")
                .trimmingCharacters(in: .whitespacesAndNewlines)
            return Double(clean)
        default: return nil
        }
    }

    var asString: String {
        switch self {
        case .string(let v): return v
        case .int(let v): return String(v)
        case .double(let v): return String(format: "%.2f", v)
        case .bool(let v): return v ? "true" : "false"
        case .null: return "-"
        }
    }
}

struct DynamicCodingKey: CodingKey {
    let stringValue: String
    let intValue: Int?

    init(_ stringValue: String) {
        self.stringValue = stringValue
        self.intValue = nil
    }

    init?(stringValue: String) {
        self.stringValue = stringValue
        self.intValue = nil
    }

    init?(intValue: Int) {
        self.stringValue = String(intValue)
        self.intValue = intValue
    }
}

extension KeyedDecodingContainer {
    func decodeLossyDoubleIfPresent(forKey key: Key) -> Double? {
        if let value = try? decodeIfPresent(Double.self, forKey: key) { return value }
        if let value = try? decodeIfPresent(Int.self, forKey: key) { return Double(value) }
        if let value = try? decodeIfPresent(String.self, forKey: key) {
            let clean = value
                .replacingOccurrences(of: "%", with: "")
                .replacingOccurrences(of: ",", with: ".")
                .trimmingCharacters(in: .whitespacesAndNewlines)
            return Double(clean)
        }
        return nil
    }

    func decodeLossyIntIfPresent(forKey key: Key) -> Int? {
        if let value = try? decodeIfPresent(Int.self, forKey: key) { return value }
        if let value = try? decodeIfPresent(Double.self, forKey: key) { return Int(value) }
        if let value = try? decodeIfPresent(String.self, forKey: key) {
            let clean = value.replacingOccurrences(of: ",", with: "").trimmingCharacters(in: .whitespacesAndNewlines)
            if let intValue = Int(clean) { return intValue }
            if let doubleValue = Double(clean) { return Int(doubleValue) }
        }
        return nil
    }
}

extension KeyedDecodingContainer where Key == DynamicCodingKey {
    func decodeLossyDoubleIfPresent(forKey key: DynamicCodingKey) -> Double? {
        if let value = try? decodeIfPresent(Double.self, forKey: key) { return value }
        if let value = try? decodeIfPresent(Int.self, forKey: key) { return Double(value) }
        if let value = try? decodeIfPresent(String.self, forKey: key) {
            let clean = value
                .replacingOccurrences(of: "%", with: "")
                .replacingOccurrences(of: ",", with: ".")
                .trimmingCharacters(in: .whitespacesAndNewlines)
            return Double(clean)
        }
        return nil
    }
}
