/** The main tool: opens the view named by the address and shows it, its progress, or its failure. */
import { Info } from "lucide-react";
import { useMemo } from "react";
import { useView } from "../api/useView";
import { TargetIndex } from "../components/SkyIndex";
import { ExploreWorkspace } from "../components/explore/ExploreWorkspace";
import { BuildFailed, BuildProgress } from "../components/panels/BuildProgress";
import type { SearchArrival } from "../components/shell/SearchBox";
import { COPY } from "../lib/copy";
import { readExploreAddress } from "../lib/exploreAddress";
import { useRoute } from "../router";

/** The note a search left for this page, if this history entry came from one. */
function arrivalNote(state: unknown): string | null {
  const note = (state as Partial<SearchArrival> | null)?.note;
  return typeof note === "string" ? note : null;
}

export function ExplorePage() {
  const route = useRoute();
  const address = useMemo(() => readExploreAddress(route.query), [route.query]);
  const { load, retry } = useView(address.request);
  const note = arrivalNote(route.state);

  return (
    <div className="page explore">
      {note && address.request && (
        <p className="note explore__note">
          <Info size={16} aria-hidden="true" />
          {note}
        </p>
      )}

      {!address.request && (
        <section className="explore__empty" aria-labelledby="explore-empty-title">
          <h1 className="section__title" id="explore-empty-title">
            {COPY.explore.emptyTitle}
          </h1>
          <p className="section__lede">{COPY.explore.emptyBody}</p>
          <TargetIndex />
        </section>
      )}

      {load.phase === "opening" && <BuildProgress status={null} />}
      {load.phase === "building" && <BuildProgress status={load.status} />}
      {load.phase === "failed" && <BuildFailed message={load.message} kind={load.kind} onRetry={retry} />}
      {load.phase === "ready" && address.request && (
        <ExploreWorkspace
          key={load.view.key}
          view={load.view}
          request={address.request}
          name={address.name}
          initial={address}
        />
      )}
    </div>
  );
}
