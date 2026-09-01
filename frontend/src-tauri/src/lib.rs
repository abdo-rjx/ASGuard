/// ASGuard desktop shell — a thin, memory-light native window around the
/// React dashboard. No heavy runtime: rendering uses the OS webview
/// (WebKitGTK on Linux, WebView2 on Windows, WKWebView on macOS).
pub fn run() {
    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("error while running the ASGuard desktop application");
}
