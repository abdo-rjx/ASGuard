/**
 * Connection state store — tracks how the desktop app gets its data.
 * Subscribable so the sidebar pill and the Settings page stay in sync.
 */

export type ConnectionStatus = "connecting" | "live" | "demo";

let status: ConnectionStatus = "connecting";
const listeners = new Set<() => void>();

export const connection = {
  get(): ConnectionStatus {
    return status;
  },
  set(next: ConnectionStatus): void {
    if (next === status) return;
    status = next;
    listeners.forEach((l) => l());
  },
  subscribe(listener: () => void): () => void {
    listeners.add(listener);
    return () => {
      listeners.delete(listener);
    };
  },
};
