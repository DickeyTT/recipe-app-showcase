import XCTest
@testable import RecipeCore
final class DemoLibraryTests: XCTestCase {
  func testDemoRecipesImportCleanlyWithCatalogueAndPhotos() throws {
    let demo = URL(fileURLWithPath: #filePath).deletingLastPathComponent()
      .appendingPathComponent("../../demo-recipes").standardizedFileURL
    let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    defer { try? FileManager.default.removeItem(at: root) }
    let store = try LibraryStore(directory: root.appendingPathComponent("Library"))
    let report = try store.importURLs([demo])
    XCTAssertEqual(report.failed, 0, report.issues.joined(separator: "\n"))
    XCTAssertEqual(report.imported, 11) // 10 recipes plus 1 note
    XCTAssertEqual(report.notesImported, 1)
    let records = try store.recipes()
    let curry = try XCTUnwrap(records.first { $0.title == "Thai green vegetable curry" })
    XCTAssertEqual(curry.collection, "Asian Cooking")
    XCTAssertTrue(curry.categories?.contains("thai") == true)
    XCTAssertEqual(curry.assetPaths.count, 1)
    XCTAssertTrue(records.allSatisfy { $0.warnings.isEmpty })
  }
}
