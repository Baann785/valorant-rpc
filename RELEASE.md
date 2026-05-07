# Release Checklist

Use this checklist before publishing a new executable or tag.

## Version

- Update `APP_VERSION` in `src/utilities/config/app_config.py`.
- Update Windows metadata in `version.py`.
- Update `README.md` current version.
- Add an entry to `CHANGELOG.md`.

## Tests

```powershell
python -B -m unittest discover -v
```

Expected result for `v3.2.7`: `46 tests OK`.

## Manual Runtime Check

- Start Discord desktop.
- Start VALORANT or let the app launch it.
- Run:
  ```powershell
  python main.py
  ```
- Confirm the tray icon appears.
- Confirm Discord shows map, agent/mode/rank where applicable.
- Confirm missing images do not produce old local Discord asset keys.
- Exit from the tray and confirm the app closes cleanly.

## Join Flow Check

Enable these config values for the manual test:

```json
"show_join_button_with_open_party": true,
"allow_join_requests": true
```

Then confirm:

- Open party button opens a local confirmation page.
- Closed party request button opens a local confirmation page.
- Riot action happens only after clicking the confirmation form button.
- Wrong region and missing token are rejected.

## Build

```powershell
.\build.bat
```

Then confirm:

- `dist/valorant-rpc.exe` is created.
- The exe starts without a Python environment.
- `favicon.ico` appears in the system tray.
- Config and logs are written under `%APPDATA%\valorant-rpc`.

## Package Notes

- Do not package old local RPC image assets.
- Keep `assets/Demo1.png` and `assets/Demo2.png` for README screenshots only.
- Keep `favicon.ico` in the PyInstaller data list.
