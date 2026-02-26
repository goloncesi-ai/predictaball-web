# Gol Oncesi Native iOS App

This iOS app is now a native SwiftUI client (not a web shell). It talks directly to the existing Gol Oncesi backend APIs.

## Implemented native modules
- Analysis (team metrics comparison)
- Simulation (league/team setup, formations, adjustments, API run + result)
- Upcoming Games (round selector + prediction cards)
- Player Lab (team filter, player profiles, compare mode)

## Open and run
1. Open [GolOncesiApp.xcodeproj](/Users/erdilsen/Library/Mobile Documents/com~apple~CloudDocs/Gol Oncesi/ios/GolOncesiApp/GolOncesiApp.xcodeproj) in Xcode.
2. Set your Apple Team in Signing & Capabilities.
3. Choose configuration:
- `Debug` = Development (`http://localhost:5001`)
- `Staging` = Staging (`https://predictaballai.com`)
- `Release` = Production (`https://predictaballai.com`)
4. Build and run on simulator/device.

## Backend configuration
Environment URLs are configured in:
- [Development.xcconfig](/Users/erdilsen/Library/Mobile Documents/com~apple~CloudDocs/Gol Oncesi/ios/GolOncesiApp/Configurations/Development.xcconfig)
- [Staging.xcconfig](/Users/erdilsen/Library/Mobile Documents/com~apple~CloudDocs/Gol Oncesi/ios/GolOncesiApp/Configurations/Staging.xcconfig)
- [Production.xcconfig](/Users/erdilsen/Library/Mobile Documents/com~apple~CloudDocs/Gol Oncesi/ios/GolOncesiApp/Configurations/Production.xcconfig)

Examples:
- Production: `https://predictaballai.com`
- Local simulator: `http://localhost:5001`
- Local device: `http://<your-mac-lan-ip>:5001`

Note: `.xcconfig` files treat `//` as comments. For `API_BASE_URL`, use host-only values (e.g. `predictaball-web.onrender.com`), not `https://...`.

## Release artifacts
- Privacy manifest: [PrivacyInfo.xcprivacy](/Users/erdilsen/Library/Mobile Documents/com~apple~CloudDocs/Gol Oncesi/ios/GolOncesiApp/GolOncesi/PrivacyInfo.xcprivacy)
- App Store checklist: [APP_STORE_READINESS.md](/Users/erdilsen/Library/Mobile Documents/com~apple~CloudDocs/Gol Oncesi/ios/GolOncesiApp/APP_STORE_READINESS.md)
- QA matrix: [QA_TEST_MATRIX.md](/Users/erdilsen/Library/Mobile Documents/com~apple~CloudDocs/Gol Oncesi/ios/GolOncesiApp/QA_TEST_MATRIX.md)
- TestFlight notes template: [TESTFLIGHT_RELEASE_TEMPLATE.md](/Users/erdilsen/Library/Mobile Documents/com~apple~CloudDocs/Gol Oncesi/ios/GolOncesiApp/TESTFLIGHT_RELEASE_TEMPLATE.md)

## App Store path (next)
- Finalize full native parity with web features (charts, deep player visuals, tactical views)
- Add app icon/launch branding pass
- Add privacy policy URL and App Privacy details
- Run TestFlight beta and crash monitoring
- Submit production build in App Store Connect
