import SwiftUI

struct MainTabView: View {
    var body: some View {
        TabView {
            AnalysisView()
                .tabItem {
                    Label("Analysis", systemImage: "chart.bar.xaxis")
                }

            SimulationView()
                .tabItem {
                    Label("Simulation", systemImage: "soccerball")
                }

            UpcomingGamesView()
                .tabItem {
                    Label("Upcoming", systemImage: "calendar")
                }

            PlayerLabView()
                .tabItem {
                    Label("Player Lab", systemImage: "person.3")
                }
        }
    }
}

#Preview {
    MainTabView()
}
