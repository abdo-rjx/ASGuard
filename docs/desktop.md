# ASGuard Desktop

The ASGuard dashboard ships as a **native desktop application** built with
[Tauri 2](https://tauri.app) — the React dashboard you already know, wrapped in a
thin native window that uses your operating system's built-in webview.

## Why Tauri (not Electron)?

| | ASGuard (Tauri) | Typical Electron app |
|---|---|---|
| RAM at idle | **~40–80 MB** (OS webview, shared runtime) | 200–400 MB (bundled Chromium) |
| Installer size | **~4–8 MB** | 120 MB+ |
| Startup | near-instant | slower (full Chromium boot) |

The `src-tauri/` Rust binary is compiled with `lto`, `opt-level = "s"` and
`strip` — the whole shell is a few MB with no Node runtime inside.

## Platforms

| Platform | Webview | Installers |
|---|---|---|
| **Fedora / Linux** | WebKitGTK 4.1 | `.deb`, `.rpm`, `.AppImage` |
| **Windows 10/11** | WebView2 (preinstalled) | `.msi`, `.exe` |
| **macOS 11+** | WKWebView | `.app` / `.dmg` (Apple Silicon + Intel) |

## Building locally (Fedora)

```bash
# one-time system dependencies
sudo dnf install webkit2gtk4.1-devel gtk3-devel librsvg2-devel patchelf

cd frontend
npm install
npm run desktop:build          # → frontend/src-tauri/target/release/bundle/
npm run desktop:dev            # hot-reloading development window
```

Build outputs on Linux:

| Artifact | Path | Notes |
|---|---|---|
| `.rpm` (Fedora) | `bundle/rpm/ASGuard-0.1.0-1.x86_64.rpm` | recommended on Fedora — uses system WebKitGTK |
| `.deb` (Debian/Ubuntu) | `bundle/deb/ASGuard_0.1.0_amd64.deb` | |
| `.AppImage` (portable) | `bundle/appimage/ASGuard-x86_64.AppImage` | self-contained (~100 MB, bundles WebKitGTK) |

> **Fedora note:** the AppImage step can fail with `failed to run linuxdeploy`
> because the bundled `strip` is too old for Fedora's very recent glibc
> (`.relr.dyn` sections). Workaround — build with strip disabled:
>
> ```bash
> cd frontend
> NO_STRIP=1 APPIMAGE_EXTRACT_AND_RUN=1 npm run desktop:build
> ```
>
> (The `.rpm` and `.deb` are unaffected.) Linux CI builds on Ubuntu don't hit
> this issue.

## Building for all platforms (CI)

GitHub Actions builds every platform automatically on every push to `main`
(see [`.github/workflows/desktop.yml`](../.github/workflows/desktop.yml)) —
download the artifacts from the workflow run page. To cut a release, push a
`v*` tag.

## Connecting to a backend

The desktop app is a **console for any ASGuard instance** — it never bundles
or touches your backend:

- **Auto-connect**: it probes `http://127.0.0.1:8000` on launch. If a backend
  is running (local `uvicorn`, Docker, or remote), the sidebar pill shows
  **LIVE** and all data is real.
- **Custom instance**: `Settings → Desktop Connection` lets you point the app
  at any backend URL. (CORS for the desktop origins is enabled server-side in
  `backend/src/asguard/api/main.py`.)
- **Offline demo mode**: with no backend reachable, the app falls back to a
  built-in simulator with realistic live traffic and the pill shows **DEMO** —
  every page (events, policies, testing, inspector) stays fully interactive.

## Files added by the desktop port

```
frontend/src-tauri/            Tauri 2 shell (Rust, window config, icons)
frontend/src/services/connection.ts    shared connection status store
frontend/src/services/demo.ts          offline demo simulator (API-compatible)
frontend/src/services/api.ts           auto-fallback + configurable backend URL
.github/workflows/desktop.yml          multi-platform build pipeline
```
