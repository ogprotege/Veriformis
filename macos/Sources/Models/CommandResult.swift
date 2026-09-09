import Foundation

/// Typed stdout from one successful command, never a digest found in a log.
struct CommandResult: Decodable {
    let schema_id: String
    let command: String
    let result: [String: String?]

    static func decode(_ process: CLIProcessResult, command: String) throws -> CommandResult {
        guard process.exitCode == 0, process.cancellation == nil,
              !process.standardOutputTruncated else {
            throw WorkbenchError.invalidConfiguration("\(command) did not return a complete successful receipt.")
        }
        let data = process.standardOutputData
        let decoded = try JSONDecoder().decode(Self.self, from: data)
        let keys: Set<String>
        switch command {
        case "split": keys = ["assignment_digest"]
        case "seal": keys = ["bundle_path", "manifest_sha256", "revision_id", "handoff_path"]
        case "package": keys = ["archive_path", "archive_sha256", "manifest_sha256", "export_receipt_sha256"]
        default: throw WorkbenchError.invalidConfiguration("Unknown command receipt: \(command)")
        }
        let object = try JSONSerialization.jsonObject(with: data) as? [String: Any]
        guard decoded.schema_id == "veriformis.command-result/v1", decoded.command == command,
              Set(object?.keys.map { $0 } ?? []) == ["schema_id", "command", "result"],
              Set(decoded.result.keys) == keys else {
            throw WorkbenchError.invalidConfiguration("\(command) returned an incompatible command receipt.")
        }
        return decoded
    }

    func text(_ key: String) throws -> String {
        guard let value = result[key] ?? nil, !value.isEmpty else {
            throw WorkbenchError.invalidConfiguration("\(command) receipt is missing \(key).")
        }
        return value
    }

    func digest(_ key: String) throws -> String {
        let value = try text(key)
        guard value.utf8.count == 64,
              value.utf8.allSatisfy({ (48 ... 57).contains($0) || (97 ... 102).contains($0) }) else {
            throw WorkbenchError.invalidConfiguration("\(command) receipt has an invalid \(key).")
        }
        return value
    }
}

/// Local UI history has its own version; it is not a compiler evidence schema.
struct RunHistoryFile: Codable {
    let schemaVersion: Int
    let entries: [RunHistoryEntry]

    init(entries: [RunHistoryEntry]) {
        schemaVersion = 1
        self.entries = entries
    }

    static func decode(_ data: Data) throws -> (entries: [RunHistoryEntry], legacy: Bool) {
        if let object = try JSONSerialization.jsonObject(with: data) as? [String: Any] {
            guard Set(object.keys) == ["schemaVersion", "entries"] else {
                throw WorkbenchError.invalidConfiguration("Run history has an unknown envelope; original bytes were preserved.")
            }
            let file = try JSONDecoder().decode(Self.self, from: data)
            guard file.schemaVersion == 1 else {
                throw WorkbenchError.invalidConfiguration("Run history version \(file.schemaVersion) is unsupported; original bytes were preserved.")
            }
            if let rawEntries = object["entries"] as? [[String: Any]] {
                for (raw, entry) in zip(rawEntries, file.entries) {
                    let knownKeys = Set(Mirror(reflecting: entry).children.compactMap(\.label))
                    guard Set(raw.keys).isSubset(of: knownKeys) else {
                        throw WorkbenchError.invalidConfiguration("Run history contains unknown entry fields; original bytes were preserved.")
                    }
                }
            }
            return (file.entries, false)
        }
        return (try JSONDecoder().decode([RunHistoryEntry].self, from: data), true)
    }
}
