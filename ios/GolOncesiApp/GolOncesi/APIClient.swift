import Foundation

enum APIError: LocalizedError {
    case invalidURL
    case invalidResponse
    case serverError(String)
    case httpError(Int, String)

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid API URL configuration."
        case .invalidResponse:
            return "Unexpected server response."
        case .serverError(let message):
            return message
        case .httpError(let code, let message):
            return "HTTP \(code): \(message)"
        }
    }
}

struct APIClient {
    static let shared = APIClient()

    private let session: URLSession
    private let decoder: JSONDecoder
    private let encoder: JSONEncoder

    init() {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = AppConfig.requestTimeout
        config.timeoutIntervalForResource = AppConfig.requestTimeout
        config.requestCachePolicy = .reloadIgnoringLocalCacheData
        session = URLSession(configuration: config)
        decoder = JSONDecoder()
        encoder = JSONEncoder()
    }

    func loadSimulationOptions() async throws -> SimulationOptionsResponse {
        try await get("/api/simulation-options")
    }

    func runSimulation(_ payload: SimulationRunRequest) async throws -> SimulationResponse {
        try await post("/api/simulate", body: payload)
    }

    func loadCurrentRound() async throws -> CurrentRoundResponse {
        try await get("/api/current-round")
    }

    func loadRecentGames(round: Int) async throws -> RecentGamesResponse {
        try await get("/api/recent-games", query: [URLQueryItem(name: "round", value: String(round))])
    }

    func loadAnalysisData(refresh: Bool = false) async throws -> AnalysisDataResponse {
        let refreshValue = refresh ? "1" : "0"
        return try await get(
            "/api/analysis-data",
            query: [
                URLQueryItem(name: "refresh", value: refreshValue)
            ]
        )
    }

    func loadPlayerAnalysis(limit: Int = 2) async throws -> PlayerAnalysisResponse {
        try await get("/api/player-analysis", query: [URLQueryItem(name: "limit", value: String(limit))])
    }

    private func get<T: Decodable>(_ path: String, query: [URLQueryItem] = []) async throws -> T {
        let url = try makeURL(path: path, query: query)
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        return try await send(request, cacheKey: url.absoluteString, allowCacheFallback: true)
    }

    private func post<T: Decodable, U: Encodable>(_ path: String, body: U) async throws -> T {
        let url = try makeURL(path: path)
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try encoder.encode(body)
        return try await send(request)
    }

    private func makeURL(path: String, query: [URLQueryItem] = []) throws -> URL {
        guard var components = URLComponents(url: AppConfig.apiBaseURL, resolvingAgainstBaseURL: false) else {
            throw APIError.serverError(
                """
                Invalid API URL configuration.

                API Base: \(AppConfig.apiBaseURL.absoluteString)
                Path: \(path)
                """
            )
        }

        // URLComponents requires an absolute path (leading "/") for host-based URLs.
        // Build a normalized path to avoid malformed URLs like "https://hostapi/endpoint".
        let endpointPath = path.hasPrefix("/") ? path : "/\(path)"
        let basePath = components.path

        if basePath.isEmpty || basePath == "/" {
            components.path = endpointPath
        } else {
            let trimmedBase = basePath.hasSuffix("/") ? String(basePath.dropLast()) : basePath
            components.path = "\(trimmedBase)\(endpointPath)"
        }
        components.queryItems = query.isEmpty ? nil : query

        guard let finalURL = components.url else {
            throw APIError.serverError(
                """
                Invalid API URL configuration.

                API Base: \(AppConfig.apiBaseURL.absoluteString)
                Path: \(path)
                """
            )
        }
        return finalURL
    }

    private func send<T: Decodable>(
        _ request: URLRequest,
        cacheKey: String? = nil,
        allowCacheFallback: Bool = false
    ) async throws -> T {
        do {
            let (data, response) = try await session.data(for: request)

            guard let http = response as? HTTPURLResponse else {
                throw APIError.invalidResponse
            }

            guard (200...299).contains(http.statusCode) else {
                if let serverMessage = try? decoder.decode([String: String].self, from: data)["error"], !serverMessage.isEmpty {
                    throw APIError.serverError(serverMessage)
                }
                let fallback = String(data: data, encoding: .utf8) ?? "Unknown error"
                throw APIError.httpError(http.statusCode, fallback)
            }

            let decoded: T
            do {
                decoded = try decoder.decode(T.self, from: data)
            } catch {
                let raw = String(data: data, encoding: .utf8) ?? ""
                throw APIError.serverError("Decoding failed: \(error.localizedDescription). Raw: \(raw.prefix(160))")
            }

            if let cacheKey {
                await APICache.shared.write(data, for: cacheKey)
            }
            return decoded
        } catch {
            if allowCacheFallback, let cacheKey, let cachedData = await APICache.shared.read(for: cacheKey) {
                if let decoded = try? decoder.decode(T.self, from: cachedData) {
                    return decoded
                }
            }
            throw enrichNetworkError(error, request: request)
        }
    }

    private func enrichNetworkError(_ error: Error, request: URLRequest) -> Error {
        guard let urlError = error as? URLError else {
            return error
        }

        let requestURL = request.url?.absoluteString ?? "unknown"
        let message = """
        \(urlError.localizedDescription)

        API Base: \(AppConfig.apiBaseURL.absoluteString)
        Request: \(requestURL)
        Env: \(AppConfig.appEnvironment)
        """
        return APIError.serverError(message)
    }
}
