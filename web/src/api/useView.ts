/** Opens a view and follows its build until it is ready or has failed. */
import { useCallback, useEffect, useState } from "react";
import { COPY } from "../lib/copy";
import { ApiError, fetchViewStatus, openView, type ViewRequest } from "./client";
import type { ErrorKind, View, ViewStatus } from "./types";
import { recallView, recallViewForRequest, rememberView } from "./viewCache";

const POLL_MS = 700;
/** A status check that fails (a network blip, a restart) is tried again this many times, this far apart. */
const POLL_RETRIES = 5;
const POLL_RETRY_MS = 2000;

export type ViewLoad =
  | { phase: "idle" }
  | { phase: "opening" }
  | { phase: "building"; status: ViewStatus }
  | { phase: "ready"; view: View }
  | { phase: "failed"; message: string; kind: ErrorKind };

/** A text that is the same for two requests exactly when they ask for the same view. */
export function requestId(request: ViewRequest): string {
  switch (request.kind) {
    case "target":
      return `target:${request.id}:${request.size ?? "own"}`;
    case "asteroid":
      return `asteroid:${request.id}`;
    case "asteroidName":
      return `asteroidName:${request.name.toLowerCase()}`;
    case "place":
      return `place:${request.ra}:${request.dec}:${request.size}`;
    case "visit":
      return `visit:${request.ra}:${request.dec}:${request.size}:${request.camera ?? "auto"}`;
  }
}

function failure(cause: unknown): ViewLoad {
  if (cause instanceof ApiError) return { phase: "failed", message: cause.message, kind: cause.kind };
  return { phase: "failed", message: COPY.errors.unexpected, kind: "internal" };
}

export function useView(request: ViewRequest | null): { load: ViewLoad; retry: () => void } {
  const id = request ? requestId(request) : null;
  // The load is stored with the request it belongs to, so a new request never shows the old view.
  const [held, setHeld] = useState<{ id: string | null; load: ViewLoad }>({ id: null, load: { phase: "idle" } });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!request || !id) return;
    const setLoad = (load: ViewLoad) => setHeld({ id, load });
    const cached = recallViewForRequest(id);
    if (cached) {
      setLoad({ phase: "ready", view: cached });
      return;
    }

    const controller = new AbortController();
    let timer: number | undefined;
    setLoad({ phase: "opening" });

    const fail = (cause: unknown) => {
      if (!controller.signal.aborted) setLoad(failure(cause));
    };

    let stumbles = 0;
    const poll = (key: string, askedForFinishedView: boolean) => {
      fetchViewStatus(key, controller.signal).then(
        (status) => {
          stumbles = 0;
          follow(status, askedForFinishedView);
        },
        (cause: unknown) => {
          if (controller.signal.aborted) return;
          const status = cause instanceof ApiError ? cause.status : 0;
          stumbles += 1;
          if (stumbles > POLL_RETRIES) {
            fail(cause);
          } else if (status === 404) {
            // The server restarted and forgot the build: ask for the view again.
            timer = window.setTimeout(() => openView(request, controller.signal).then((s) => follow(s, false), fail), POLL_RETRY_MS);
          } else if (status === 0 || status >= 500) {
            timer = window.setTimeout(() => poll(key, askedForFinishedView), POLL_RETRY_MS);
          } else {
            fail(cause);
          }
        },
      );
    };

    const follow = (status: ViewStatus, askedForFinishedView: boolean) => {
      if (controller.signal.aborted) return;
      if (status.state === "failed") {
        setLoad({
          phase: "failed",
          message: status.error ?? COPY.errors.unexpected,
          kind: status.error_kind ?? "internal",
        });
      } else if (status.state === "ready") {
        if (status.view) {
          rememberView(status.view, id);
          setLoad({ phase: "ready", view: status.view });
        } else if (askedForFinishedView) {
          setLoad({ phase: "failed", message: COPY.errors.unexpected, kind: "internal" });
        } else {
          poll(status.key, true);
        }
      } else {
        setLoad({ phase: "building", status });
        timer = window.setTimeout(() => poll(status.key, false), POLL_MS);
      }
    };

    openView(request, controller.signal).then((status) => follow(status, false), fail);

    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
    // `id` stands for `request`: two requests with the same id open the same view.
  }, [id, attempt]);

  const retry = useCallback(() => setAttempt((n) => n + 1), []);
  const load: ViewLoad = !id ? { phase: "idle" } : held.id === id ? held.load : { phase: "opening" };
  return { load, retry };
}

/**
 * A view that is already built, by its key: for previews and thumbnails. Never starts a
 * build; gives `null` until the view arrives, and stays `null` if it is not ready.
 */
export function useReadyView(key: string | null): View | null {
  const [view, setView] = useState<View | null>(() => (key ? (recallView(key) ?? null) : null));

  useEffect(() => {
    if (!key) {
      setView(null);
      return;
    }
    const cached = recallView(key);
    if (cached) {
      setView(cached);
      return;
    }
    const controller = new AbortController();
    fetchViewStatus(key, controller.signal).then(
      (status) => {
        if (status.state === "ready" && status.view) {
          rememberView(status.view);
          setView(status.view);
        }
      },
      () => {
        // A preview that cannot load simply stays empty; the page explains itself without it.
      },
    );
    return () => controller.abort();
  }, [key]);

  return view;
}
