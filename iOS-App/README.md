# iPhone and iPad app

Open `RecipeApp.xcodeproj`, select the **RecipeMobile** scheme and an iPhone or iPad simulator, and run. The target uses the local `RecipeCore` package and supports iOS/iPadOS 15 and later. No signing team is set; choose your own to run on a device.

The app is for browsing and cooking: collections, catalogue and ingredient search with filters, favourites, notes, offline photos and PDF references, view and cook counts, and cooking mode with "Keep screen on". Recipes are edited and imported on the Mac.

Recipes arrive by syncing with the Mac app over the local network (the Sync button on each side). A Debug build adds a few sample recipes on first launch so the Simulator has something to show.

`../Scripts/check-ios.sh` compiles and links the shared code and this app for iOS 15 without launching anything.
