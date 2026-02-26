import SwiftUI

struct FormationPitchView: View {
    let formation: String
    let teamName: String
    let tint: Color
    var mirrorHorizontally: Bool = false

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(teamName)
                .font(.caption)
                .fontWeight(.semibold)
            Text(formation)
                .font(.caption2)
                .foregroundStyle(.secondary)

            GeometryReader { proxy in
                let width = proxy.size.width
                let height = proxy.size.height

                ZStack {
                    RoundedRectangle(cornerRadius: 12)
                        .fill(
                            LinearGradient(
                                colors: [Color.green.opacity(0.28), Color.green.opacity(0.17)],
                                startPoint: .top,
                                endPoint: .bottom
                            )
                        )

                    RoundedRectangle(cornerRadius: 12)
                        .stroke(Color.white.opacity(0.35), lineWidth: 1)

                    Rectangle()
                        .stroke(Color.white.opacity(0.4), lineWidth: 1)
                        .frame(width: width * 0.96, height: height * 0.95)

                    Circle()
                        .stroke(Color.white.opacity(0.4), lineWidth: 1)
                        .frame(width: min(width, height) * 0.23)

                    ForEach(Array(playerPoints(width: width, height: height).enumerated()), id: \.offset) { index, point in
                        Circle()
                            .fill(tint.opacity(0.95))
                            .frame(width: 14, height: 14)
                            .overlay {
                                Text("\(index + 1)")
                                    .font(.system(size: 7, weight: .bold))
                                    .foregroundStyle(.white)
                            }
                            .position(x: point.x, y: point.y)
                    }
                }
            }
            .frame(height: 180)
        }
    }

    private func playerPoints(width: CGFloat, height: CGFloat) -> [CGPoint] {
        let numbers = formation
            .split(separator: "-")
            .compactMap { Int($0) }
            .filter { $0 > 0 }

        let lines: [Int]
        if numbers.reduce(0, +) == 10 {
            lines = numbers
        } else {
            lines = [4, 4, 2]
        }

        var points: [CGPoint] = []

        // Goalkeeper
        points.append(
            CGPoint(
                x: mirrorHorizontally ? width * 0.90 : width * 0.10,
                y: height * 0.50
            )
        )

        let usableStartX = mirrorHorizontally ? 0.78 : 0.22
        let usableEndX = mirrorHorizontally ? 0.22 : 0.78
        let step = (usableEndX - usableStartX) / CGFloat(max(lines.count - 1, 1))

        for (lineIndex, count) in lines.enumerated() {
            let xFactor = usableStartX + (CGFloat(lineIndex) * step)

            if count == 1 {
                points.append(CGPoint(x: width * xFactor, y: height * 0.50))
                continue
            }

            for i in 0..<count {
                let yFactor = CGFloat(i + 1) / CGFloat(count + 1)
                points.append(
                    CGPoint(
                        x: width * xFactor,
                        y: height * yFactor
                    )
                )
            }
        }

        return Array(points.prefix(11))
    }
}

#Preview {
    HStack {
        FormationPitchView(formation: "4-2-3-1", teamName: "Home", tint: .blue)
        FormationPitchView(formation: "3-4-3", teamName: "Away", tint: .red, mirrorHorizontally: true)
    }
    .padding()
}
