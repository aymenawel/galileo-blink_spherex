/**
 * A very small router on the browser's History API.
 *
 * The address bar is the single source of truth: `useRoute()` re-renders a component when
 * the address changes, `navigate()` changes it, and `<Link>` is an ordinary anchor that
 * does so without reloading the page.
 */
import { createElement, useSyncExternalStore, type AnchorHTMLAttributes, type MouseEvent } from "react";

export interface Route {
  /** The path, without a trailing slash (the home page is "/"). */
  path: string;
  query: URLSearchParams;
  /** The fragment without its "#", or "". */
  hash: string;
  /** Whatever was passed to `navigate()` as `state` for this entry. */
  state: unknown;
}

export interface NavigateOptions {
  /** Rewrite the current history entry instead of adding one. */
  replace?: boolean;
  /** Extra information for the next page that does not belong in a shareable address. */
  state?: unknown;
}

function readRoute(): Route {
  const { pathname, search, hash } = window.location;
  return {
    path: pathname.length > 1 ? pathname.replace(/\/+$/, "") : "/",
    query: new URLSearchParams(search),
    hash: hash.replace(/^#/, ""),
    state: window.history.state as unknown,
  };
}

let current: Route = readRoute();
const listeners = new Set<() => void>();

function publish(): void {
  current = readRoute();
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

window.addEventListener("popstate", publish);

/** Bring the part of the page named by the address into view once it has been drawn. */
function settleScroll(hash: string): void {
  window.requestAnimationFrame(() => {
    const anchor = hash ? document.getElementById(hash) : null;
    if (anchor) anchor.scrollIntoView({ block: "start" });
    else window.scrollTo(0, 0);
  });
}

export function navigate(to: string, options: NavigateOptions = {}): void {
  if (options.replace) {
    // Rewriting an entry keeps what was attached to it unless something new is given.
    const state: unknown = options.state !== undefined ? options.state : window.history.state;
    window.history.replaceState(state, "", to);
  } else {
    window.history.pushState(options.state ?? null, "", to);
  }
  publish();
  if (!options.replace) settleScroll(current.hash);
}

export function useRoute(): Route {
  return useSyncExternalStore(subscribe, () => current);
}

function isPlainLeftClick(event: MouseEvent): boolean {
  return event.button === 0 && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey;
}

export interface LinkProps extends Omit<AnchorHTMLAttributes<HTMLAnchorElement>, "href"> {
  to: string;
}

/** An anchor to another page of this site. Opens in a new tab as usual with a modifier key. */
export function Link({ to, onClick, ...rest }: LinkProps) {
  return createElement("a", {
    ...rest,
    href: to,
    onClick: (event: MouseEvent<HTMLAnchorElement>) => {
      onClick?.(event);
      if (event.defaultPrevented || !isPlainLeftClick(event) || rest.target) return;
      event.preventDefault();
      navigate(to);
    },
  });
}
