# App Store Readiness Checklist

## Build and release configuration
- [ ] Build with `Release` (Production API).
- [ ] Verify `API_BASE_URL` resolves to production endpoint.
- [ ] Confirm `APP_ENV` in app settings is `Production`.

## Metadata and legal
- [ ] App name, subtitle, keywords finalized.
- [ ] Privacy Policy URL added in App Store Connect.
- [ ] Support URL added in App Store Connect.
- [ ] Age rating questionnaire completed.

## Privacy and compliance
- [ ] Validate [PrivacyInfo.xcprivacy](/Users/erdilsen/Library/Mobile Documents/com~apple~CloudDocs/Gol Oncesi/ios/GolOncesiApp/GolOncesi/PrivacyInfo.xcprivacy).
- [ ] Complete App Privacy nutrition labels in App Store Connect.
- [ ] Confirm no tracking and no ATT prompt required.

## Quality gates
- [ ] Run full QA matrix: [QA_TEST_MATRIX.md](/Users/erdilsen/Library/Mobile Documents/com~apple~CloudDocs/Gol Oncesi/ios/GolOncesiApp/QA_TEST_MATRIX.md).
- [ ] Validate offline fallback behavior after first online load.
- [ ] Validate API error states on each tab.
- [ ] Validate orientation and dynamic type behavior.

## Submission flow
- [ ] Upload build via Xcode Organizer.
- [ ] Distribute to TestFlight internal testers.
- [ ] Resolve all blocking feedback.
- [ ] Submit for App Review with production release notes.
