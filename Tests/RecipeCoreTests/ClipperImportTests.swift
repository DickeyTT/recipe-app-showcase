import CoreData
import XCTest
@testable import RecipeCore

/// Guards the Chrome clipper's contract with the importer. Confirms a bundle
/// shaped exactly as chrome-clipper produces imports as a recipe, with its image,
/// in the RecipeClips collection, flagged for review.
final class ClipperImportTests: XCTestCase {
  func testClipperBundleImports() throws {
    let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    let clips = root.appendingPathComponent("RecipeClips")
    let base = "spiced-lamb-flatbreads-202610292100"
    // Each clip lives in its own folder with a notebook-labels.json overriding
    // the collection, exactly as chrome-clipper writes it.
    let source = clips.appendingPathComponent(base)
    try FileManager.default.createDirectory(at: source, withIntermediateDirectories: true)
    addTeardownBlock { try? FileManager.default.removeItem(at: root) }
    try JSONSerialization.data(withJSONObject: [base: "Web Clips"]).write(to: source.appendingPathComponent("notebook-labels.json"))
    let png = Data(base64Encoded: "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M8AAAMBAQDJ/pLvAAAAAElFTkSuQmCC")!
    try png.write(to: source.appendingPathComponent("\(base).jpg"))
    // Two in-body step photos, each distinct bytes so they get distinct assets.
    try (png + Data([1])).write(to: source.appendingPathComponent("\(base)-img-1.jpg"))
    try (png + Data([2])).write(to: source.appendingPathComponent("\(base)-img-2.jpg"))

    let markdown = """
    ---
    source url: https://example.com/lamb
    created at: 2024-03-02
    ---

    # Spiced Lamb Flatbreads

    ![[\(base).jpg]]

    ## Ingredients

    - 500g lamb mince
    - 1 tsp cumin

    ## Method

    1. Brown the lamb.
    2. Pile onto flatbreads.

    ## Notes

    Rest the lamb before serving.

    ## Tips

    - Toast the flatbreads.

    ![[\(base)-img-1.jpg]]

    Step photo one.

    ![[\(base)-img-2.jpg]]

    ## Source

    https://example.com/lamb
    """
    try markdown.write(to: source.appendingPathComponent("\(base).md"), atomically: true, encoding: .utf8)

    let sidecar: [String: Any] = ["isRecipe": true, "confidence": 1, "categories": ["meat", "main-dishes"], "tags": ["quick", "one-pot"], "ingredients": ["500g lamb mince", "1 tsp cumin"], "cuisine": "Middle Eastern"]
    try JSONSerialization.data(withJSONObject: sidecar).write(to: source.appendingPathComponent("\(base).catalogue.json"))

    let store = try LibraryStore(directory: root.appendingPathComponent("Library"))
    // Import the top-level RecipeClips folder, as the user would.
    XCTAssertEqual(try store.importURLs([clips]).imported, 1)

    let recipe = try XCTUnwrap(try store.recipes().first)
    XCTAssertEqual(recipe.title, "Spiced Lamb Flatbreads")
    XCTAssertEqual(recipe.collection, "Web Clips")
    XCTAssertEqual(recipe.sourceURL, "https://example.com/lamb")
    XCTAssertEqual(recipe.ingredients?.count, 2)
    // Categories and tags from the sidecar drive browsing and search.
    XCTAssertEqual(Set(recipe.categories ?? []), ["meat", "main-dishes"])
    XCTAssertEqual(Set(recipe.tags ?? []), ["quick", "one-pot"])
    XCTAssertTrue(CatalogueVocabulary.hasCategory(recipe, "meat"))
    XCTAssertEqual(recipe.assetPaths.count, 3, "hero plus two step photos should be copied in")
    XCTAssertEqual(recipe.blocks.filter { $0.kind == .image }.count, 3, "three image blocks expected")
    XCTAssertFalse(recipe.needsReview, "a catalogued clip (confidence 1) should skip Needs review")
    // The extra prose (notes, tips) must survive import as content blocks.
    XCTAssertTrue(recipe.blocks.contains { $0.kind == .heading && $0.text == "Notes" }, "Notes heading expected")
    XCTAssertTrue(recipe.blocks.contains { $0.text.contains("Rest the lamb") }, "notes text expected")
  }
}
