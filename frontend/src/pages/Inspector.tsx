import { useParams } from "react-router-dom";
import { api } from "../services/api";
import { useApi } from "../hooks/useApi";
import { EventDetailBody } from "./EventDetail";
import type { SecurityEvent } from "../types";

/** Request Inspector — full transaction lifecycle for one event. */
export function Inspector() {
  const { id } = useParams();
  const { data: event, error, loading } = useApi<SecurityEvent | null>(
    () => (id ? api.event(id) : api.events({ limit: 1 }).then((r) => r.events[0] ?? null)),
    [id],
  );

  if (loading) return <div className="empty"><span className="spinning" /> Loading transaction…</div>;
  if (error || !event) return <div className="empty">{error ?? "No transaction selected."}</div>;

  return <EventDetailBody event={event} />;
}