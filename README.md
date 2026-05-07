# Valorant Discord Rich Presence

```
 _   _____   __   ____  ___  ___   _  ________
| | / / _ | / /  / __ \/ _ \/ _ | / |/ /_  __/__________  ____
| |/ / __ |/ /__/ /_/ / , _/ __ |/    / / / /___/ __/ _ \/ __/
|___/_/ |_/____/\____/_/|_/_/ |_/_/|_/ /_/     /_/ / .__/\__/
                                                   /_/
```

**Current version:** `v3.2.7`

Maintained fork of the original [valorant-rpc](https://github.com/colinhartigan/valorant-rpc) project. The original repository has been archived; this fork keeps the app working with current Valorant API behavior.

## Features

- Real-time Discord Rich Presence for VALORANT
- Current state, map, agent, mode, party state, queue timer, and score
- Competitive rank display when enabled
- Valorant-API image URLs for agents, maps, ranks, and modes
- Local cached Valorant content fallback when the network is unavailable
- Optional secured local join/request confirmation flow
- Windows tray icon with config, reload, show/hide window, and exit actions

## Screenshots

<img src="assets/Demo1.png" alt="Valorant RPC demo 1" width="205" height="112">
<img src="assets/Demo2.png" alt="Valorant RPC demo 2" width="205" height="112">

## Requirements

- Windows
- Python 3.10+
- Discord desktop app
- VALORANT / Riot Client

## Install And Run

```powershell
python -m pip install -r requirements.txt
python main.py
```

Recommended manual test flow:

1. Start Discord.
2. Start VALORANT or let the app launch it.
3. Run `python main.py`.
4. Confirm the Discord profile shows your VALORANT status.
5. Use the tray icon to reload, edit config, or exit.

## Configuration

The app stores its runtime config under:

```text
%APPDATA%\valorant-rpc\config.json
```

Useful options:

- `region`: auto-detected on first launch when possible.
- `presence_refresh_interval`: Discord presence refresh interval in seconds.
- `presences.menu.show_rank_in_comp_lobby`: show rank while waiting in competitive lobby.
- `presences.modes.all.large_image`: choose `map`, `agent`, or `rank`.
- `presences.modes.all.small_image`: choose `map`, `agent`, or `rank`.
- `presences.menu.show_join_button_with_open_party`: show a join button for open parties.
- `presences.menu.allow_join_requests`: show a request button for closed parties.
- `webserver.port`: local confirmation server port, default `4100`.

Join links are disabled by default. Enable them only if you want Discord buttons that open a local confirmation page.

## Secure Join Flow

Discord buttons can only open URLs, so the app never performs a Riot action directly from a Discord click.

The secured flow is:

1. Discord opens `http://127.0.0.1:<port>/valorant/confirm/...`.
2. The local page shows the party and region.
3. The user confirms with a form button.
4. The form sends a token-gated `POST` to the local server.
5. The local server validates token, region, identifiers, and origin before calling Riot.

The token is per run and is not placed in the Discord button URL.

## Build

```powershell
.\build.bat
```

The build script installs dependencies and runs:

```powershell
python -m PyInstaller valorant-rpc.spec --clean --noconfirm
```

The generated executable is written to `dist/`. The PyInstaller spec packages `favicon.ico` only; runtime RPC images come from Valorant-API URLs.

## Tests

```powershell
python -B -m unittest discover -v
```

The `-B` flag avoids recreating Python bytecode files during test runs.

Current coverage includes:

- config creation, migration, and corruption recovery
- Valorant content loading and cache fallback
- partial Riot presence payloads
- Discord RPC image URL sanitization
- systray shutdown behavior
- secured local join/request flow
- prevention of old local Discord asset keys

## Troubleshooting

### Discord presence does not show

- Make sure the Discord desktop app is running.
- Restart the app from the tray icon.
- Check `%APPDATA%\valorant-rpc\rpc.log`.

### VALORANT region is wrong

- Start VALORANT once, then restart the RPC.
- If auto-detection fails, edit `region` in the config file.

### Images are missing or Discord shows a blank placeholder

- The app only sends HTTP(S) Valorant-API image URLs to Discord.
- If Valorant-API is temporarily unavailable, the app falls back to cached content.
- If no valid URL exists, the app sends no image instead of an old local asset key.

### Join button opens a page but the action is rejected

- Confirm the region shown on the page matches your client.
- Make sure the app is still running locally.
- Check that the local port is not blocked or already used by another app.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## Release Checklist

See [RELEASE.md](RELEASE.md) before publishing an executable or tag.

## Credits

- Original project by [colinhartigan](https://github.com/colinhartigan/valorant-rpc)
- Maintained fork with fixes for current VALORANT API behavior

## Disclaimer

This project is not affiliated with Riot Games or any of its employees and therefore does not reflect the views of said parties.

Riot Games does not endorse or sponsor this project. Riot Games, and all associated properties are trademarks or registered trademarks of Riot Games, Inc.

## License

This project is licensed under the MIT License. See [LICENSE.txt](LICENSE.txt).
