import SwiftUI
import Charts

struct OutcomeProbabilityChart: View {
    let home: Double
    let draw: Double
    let away: Double

    private var rows: [(label: String, value: Double, color: Color)] {
        [
            ("Home", home, .blue),
            ("Draw", draw, .orange),
            ("Away", away, .red)
        ]
    }

    var body: some View {
        Chart(rows, id: \.label) { row in
            BarMark(
                x: .value("Outcome", row.label),
                y: .value("Probability", row.value)
            )
            .foregroundStyle(row.color)
            .annotation(position: .top) {
                Text(String(format: "%.1f%%", row.value))
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }
        }
        .chartYScale(domain: 0...100)
        .frame(height: 180)
    }
}

struct GoalTrendChart: View {
    let homeTeam: String
    let awayTeam: String
    let homeHistory: [TeamMatchHistory]
    let awayHistory: [TeamMatchHistory]

    private struct Point: Identifiable {
        let id = UUID()
        let index: Int
        let team: String
        let goalsFor: Double
        let color: Color
    }

    private var points: [Point] {
        let home = Array(homeHistory.prefix(10)).reversed().enumerated().map {
            Point(index: $0.offset + 1, team: homeTeam, goalsFor: Double($0.element.goalsFor), color: .blue)
        }
        let away = Array(awayHistory.prefix(10)).reversed().enumerated().map {
            Point(index: $0.offset + 1, team: awayTeam, goalsFor: Double($0.element.goalsFor), color: .red)
        }
        return home + away
    }

    var body: some View {
        Chart(points) { point in
            LineMark(
                x: .value("Match", point.index),
                y: .value("Goals", point.goalsFor)
            )
            .foregroundStyle(by: .value("Team", point.team))

            PointMark(
                x: .value("Match", point.index),
                y: .value("Goals", point.goalsFor)
            )
            .foregroundStyle(by: .value("Team", point.team))
        }
        .chartForegroundStyleScale([
            homeTeam: Color.blue,
            awayTeam: Color.red
        ])
        .chartYScale(domain: 0...5)
        .frame(height: 220)
    }
}

struct PlayerComparisonChart: View {
    let playerAName: String
    let playerBName: String
    let rows: [MetricRow]

    struct MetricRow: Identifiable {
        let id = UUID()
        let metric: String
        let valueA: Double
        let valueB: Double
    }

    private struct ChartPoint: Identifiable {
        let id = UUID()
        let metric: String
        let player: String
        let value: Double
    }

    private var points: [ChartPoint] {
        rows.flatMap { row in
            [
                ChartPoint(metric: short(row.metric), player: playerAName, value: row.valueA),
                ChartPoint(metric: short(row.metric), player: playerBName, value: row.valueB)
            ]
        }
    }

    var body: some View {
        Chart(points) { point in
            BarMark(
                x: .value("Metric", point.metric),
                y: .value("Value", point.value)
            )
            .position(by: .value("Player", point.player))
            .foregroundStyle(by: .value("Player", point.player))
        }
        .chartYAxis {
            AxisMarks(position: .leading)
        }
        .frame(height: 220)
    }

    private func short(_ metric: String) -> String {
        if metric.count <= 10 { return metric }
        return String(metric.prefix(10)) + "…"
    }
}
