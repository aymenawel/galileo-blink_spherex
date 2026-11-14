/** Small facts fetched once per visit and shared by every component that needs them. */
import { useEffect, useState } from "react";
import { ApiError, fetchAbout, fetchTargets } from "./client";
import type { About, Target } from "./types";

export type Resource<T> =
  | { status: "loading" }
  | { status: "ready"; data: T }
  | { status: "failed"; message: string };

const inFlight = new Map<string, Promise<unknown>>();

function loadOnce<T>(name: string, load: () => Promise<T>): Promise<T> {
  const existing = inFlight.get(name) as Promise<T> | undefined;
  if (existing) return existing;
  const started = load();
  inFlight.set(name, started);
  // A failed load is forgotten so the next visit to the page tries again.
  started.catch(() => inFlight.delete(name));
  return started;
}

function useResource<T>(name: string, load: () => Promise<T>): Resource<T> {
  const [resource, setResource] = useState<Resource<T>>({ status: "loading" });

  useEffect(() => {
    let current = true;
    loadOnce(name, load).then(
      (data) => current && setResource({ status: "ready", data }),
      (cause: unknown) =>
        current &&
        setResource({
          status: "failed",
          message: cause instanceof ApiError ? cause.message : String(cause),
        }),
    );
    return () => {
      current = false;
    };
  }, [name, load]);

  return resource;
}

const loadTargets = () => fetchTargets();
const loadAbout = () => fetchAbout();

/** NASA's five test targets. */
export function useTargets(): Resource<Target[]> {
  return useResource("targets", loadTargets);
}

/** Camera bands, field limits and the meaning of NASA's quality flags. */
export function useAbout(): Resource<About> {
  return useResource("about", loadAbout);
}
