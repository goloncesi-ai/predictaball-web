import Foundation
import CryptoKit

actor APICache {
    static let shared = APICache()

    private let cacheDirectory: URL

    init(fileManager: FileManager = .default) {
        let root = fileManager.urls(for: .cachesDirectory, in: .userDomainMask).first
            ?? URL(fileURLWithPath: NSTemporaryDirectory())
        cacheDirectory = root.appendingPathComponent("GolOncesiAPI", isDirectory: true)

        if !fileManager.fileExists(atPath: cacheDirectory.path) {
            try? fileManager.createDirectory(at: cacheDirectory, withIntermediateDirectories: true)
        }
    }

    func write(_ data: Data, for key: String) {
        let url = fileURL(for: key)
        try? data.write(to: url, options: [.atomic])
    }

    func read(for key: String) -> Data? {
        let url = fileURL(for: key)
        return try? Data(contentsOf: url)
    }

    private func fileURL(for key: String) -> URL {
        let digest = SHA256.hash(data: Data(key.utf8))
        let name = digest.compactMap { String(format: "%02x", $0) }.joined()
        return cacheDirectory.appendingPathComponent(name).appendingPathExtension("json")
    }
}
