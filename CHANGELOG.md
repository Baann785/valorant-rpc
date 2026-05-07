# Changelog

All notable changes to this maintained fork are documented here.

## v3.2.7 - 2026-05-07

### Added

- Secure Discord join/request button flow using a local confirmation page.
- Local confirmation routes for open-party join and closed-party request actions.
- Security tests for token-gated `POST`, region validation, origin checks, identifier validation, and response headers.
- README sections for configuration, secure join flow, build, tests, and troubleshooting.

### Changed

- Discord button URLs now open a local confirmation page instead of exposing action tokens.
- The local webserver starts only when join/request features are enabled.
- Runtime metadata and Windows file metadata are unified on `v3.2.7`.

### Security

- Riot join/request actions remain `POST` only.
- Local action tokens are per run and are not included in Discord button URLs.
- Local server responses include no-store and frame/CSP hardening headers.

## v3.2.6 - 2026-05-07

### Added

- Graceful systray shutdown without forced process exit.
- Central Discord RPC image sanitizer that accepts only HTTP(S) URLs.
- Regression tests for partial Riot payloads, systray shutdown, and old local asset keys.

### Changed

- The presence loop continues in degraded mode when Riot or Discord data is temporarily missing.
- Build script no longer requests administrator elevation.
- PyInstaller packaging keeps `favicon.ico` but does not package the old local RPC assets.

### Fixed

- Silent `PhaseError` handling now writes useful debug logs.
- Invalid or missing RPC images are sent as `None` instead of empty strings or old local asset keys.

## v3.2.5 - 2025-12-20

### Added

- Shared HTTP client behavior with timeouts and HTTP validation.
- Valorant content cache fallback.
- Config migration and corruption backup tests.

### Changed

- Agents, maps, ranks, and modes use Valorant-API HTTPS image URLs.
- Runtime/build metadata was unified on `v3.2.5`.

### Security

- Local webserver actions were moved behind localhost-only, token-gated `POST` requests.

### Fixed

- Crash when entering the Shooting Range due to missing `sessionLoopState`.
- Several partial Riot payload crashes through safer `.get()` access.

## v3.2.4 - 2025-12-19

### Added

- Improved matchmaking queue state detection.
- Party state detection from `partyPresenceData` and `matchPresenceData`.

### Changed

- Presence files were updated to use safer key access patterns.

### Fixed

- `sessionLoopState` detection moved to `matchPresenceData`.
- `accountLevel` retrieval moved to `playerPresenceData`.
- In-game status now shows game mode and score more reliably.
- Shooting Range detection via `provisioningFlow`.
