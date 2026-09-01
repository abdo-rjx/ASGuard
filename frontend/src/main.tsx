import React from "react";
import ReactDOM from "react-dom/client";
// HashRouter: works both when served by the FastAPI backend and inside the
// Tauri desktop webview (no server-side routing to lean on).
import { HashRouter } from "react-router-dom";
import App from "./App";
import { probeBackend } from "./services/api";
import "./styles.css";

// Determine connection state as early as possible so the sidebar pill is
// correct on first paint.
void probeBackend();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <HashRouter>
      <App />
    </HashRouter>
  </React.StrictMode>,
);
