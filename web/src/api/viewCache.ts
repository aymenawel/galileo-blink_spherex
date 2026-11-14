/** Views already downloaded in this visit, so going back to one is instant. */
import type { View } from "./types";

const byKey = new Map<string, View>();
const keyOfRequest = new Map<string, string>();

export function rememberView(view: View, requestId?: string): void {
  byKey.set(view.key, view);
  if (requestId) keyOfRequest.set(requestId, view.key);
}

export function recallView(key: string): View | undefined {
  return byKey.get(key);
}

export function recallViewForRequest(requestId: string): View | undefined {
  const key = keyOfRequest.get(requestId);
  return key ? byKey.get(key) : undefined;
}
