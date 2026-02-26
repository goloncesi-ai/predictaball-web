import Foundation

enum AppConfig {
    private static let defaultAPIBase = "https://predictaball-web.onrender.com"
    private static let defaultEnvironment = "Development"

    static var apiBaseURL: URL {
        let rawValue = (Bundle.main.object(forInfoDictionaryKey: "API_BASE_URL") as? String)?.trimmingCharacters(in: .whitespacesAndNewlines)
        let fallback = URL(string: defaultAPIBase)!

        guard var input = rawValue, !input.isEmpty else {
            return fallback
        }

        input = input.trimmingCharacters(in: CharacterSet(charactersIn: "\"'"))

        // If build settings were not expanded (e.g. "$(API_BASE_URL)"), use production fallback.
        if input.contains("$(") || input.contains(")") {
            return fallback
        }

        // Protect against xcconfig truncation (e.g. "https:" when "//" is parsed as comment).
        if input == "http:" || input == "https:" {
            return fallback
        }

        if let direct = URL(string: input), direct.scheme != nil, let host = direct.host, !host.isEmpty {
            #if !targetEnvironment(simulator)
            let normalized = host.lowercased()
            if normalized == "localhost" || normalized == "127.0.0.1" {
                return fallback
            }
            #endif
            return direct
        }

        let localHost = input.lowercased().hasPrefix("localhost") || input.hasPrefix("127.0.0.1")
        let scheme = localHost ? "http" : "https"
        let resolved = URL(string: "\(scheme)://\(input)") ?? fallback
        #if !targetEnvironment(simulator)
        if let host = resolved.host?.lowercased(), host == "localhost" || host == "127.0.0.1" {
            return fallback
        }
        #endif
        return resolved
    }

    static var appEnvironment: String {
        let rawValue = (Bundle.main.object(forInfoDictionaryKey: "APP_ENV") as? String)?.trimmingCharacters(in: .whitespacesAndNewlines)
        if let rawValue, !rawValue.isEmpty {
            return rawValue
        }
        return defaultEnvironment
    }

    static let requestTimeout: TimeInterval = 90
}
