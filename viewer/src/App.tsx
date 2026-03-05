import { useCallback, useMemo, useState } from "react";
import { useTraceList, useTrace, useMultiTrace } from "./hooks/useTraces";
import { TraceList } from "./components/TraceList";
import { TraceTree } from "./components/TraceTree";
import { TraceTimeline } from "./components/TraceTimeline";
import { TraceGraph } from "./components/TraceGraph";
import { ViewToggle, type ViewMode } from "./components/ViewToggle";
import { NodeDetail } from "./components/NodeDetail";
import { mergeTraces, type TraceOriginMap } from "./lib/merge";
import "./App.css";

export type TimeMode = "absolute" | "normalized";

export default function App() {
  const { traces, error: listError, newCount, clearNewCount } = useTraceList();
  const [selectedTraceIds, setSelectedTraceIds] = useState<Set<string>>(new Set());
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("tree");
  const [timeMode, setTimeMode] = useState<TimeMode>("absolute");

  const selectedArray = useMemo(() => [...selectedTraceIds], [selectedTraceIds]);
  const primaryTraceId = selectedArray[0] ?? null;

  const usesMultiData = viewMode === "timeline" || viewMode === "graph";

  const { trace: singleTrace, loading: singleLoading, error: singleError } = useTrace(
    !usesMultiData ? primaryTraceId : null,
  );

  const {
    traces: multiTraces,
    loading: multiLoading,
    error: multiError,
  } = useMultiTrace(usesMultiData ? selectedArray : []);

  const { merged, origins } = useMemo<{
    merged: ReturnType<typeof mergeTraces>["merged"] | null;
    origins: TraceOriginMap | null;
  }>(() => {
    if (multiTraces.length === 0) return { merged: null, origins: null };
    if (multiTraces.length === 1)
      return { merged: multiTraces[0], origins: null };
    const result = mergeTraces(multiTraces, timeMode);
    return result;
  }, [multiTraces, timeMode]);

  const handleSelect = useCallback((id: string) => {
    setSelectedTraceIds(new Set([id]));
    setSelectedNodeId(null);
    clearNewCount();
  }, [clearNewCount]);

  const handleToggle = useCallback((id: string) => {
    setSelectedTraceIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
    setSelectedNodeId(null);
  }, []);

  const handleSelectSession = useCallback((traceIds: string[]) => {
    setSelectedTraceIds(new Set(traceIds));
    setSelectedNodeId(null);
    clearNewCount();
  }, [clearNewCount]);

  const isMulti = selectedTraceIds.size > 1;

  const activeTrace = usesMultiData ? merged : singleTrace;
  const loading = usesMultiData ? multiLoading : singleLoading;
  const traceError = usesMultiData ? multiError : singleError;

  const totalNodes = activeTrace ? Object.keys(activeTrace.nodes).length : 0;
  const selectedNode = activeTrace && selectedNodeId
    ? activeTrace.nodes[selectedNodeId] ?? null
    : null;

  return (
    <div className="app">
      <TraceList
        traces={traces}
        selectedIds={selectedTraceIds}
        onSelect={handleSelect}
        onToggle={handleToggle}
        onSelectSession={handleSelectSession}
        newCount={newCount}
        onClearNew={clearNewCount}
        multiSelect={usesMultiData}
      />

      <main className="main-panel">
        {listError && <div className="error-banner">{listError}</div>}
        {traceError && <div className="error-banner">{traceError}</div>}

        {selectedTraceIds.size === 0 && (
          <div className="empty-main">
            <p>Select a trace from the sidebar to inspect it.</p>
          </div>
        )}

        {loading && <div className="loading">Loading trace…</div>}

        {activeTrace && !loading && (
          <>
            <div className="main-panel-header">
              <div className="main-panel-title">
                <h2>{activeTrace.name || activeTrace.trace_id}</h2>
                <span className="trace-meta">{totalNodes} nodes</span>
              </div>
              <ViewToggle mode={viewMode} onChange={setViewMode} />
            </div>

            {viewMode === "tree" && (
              <TraceTree
                trace={activeTrace}
                selectedNodeId={selectedNodeId}
                onSelectNode={setSelectedNodeId}
              />
            )}

            {viewMode === "timeline" && (
              <TraceTimeline
                trace={activeTrace}
                selectedNodeId={selectedNodeId}
                onSelectNode={setSelectedNodeId}
                origins={origins}
                timeMode={timeMode}
                onTimeModeChange={isMulti ? setTimeMode : undefined}
              />
            )}

            {viewMode === "graph" && (
              <TraceGraph
                trace={activeTrace}
                selectedNodeId={selectedNodeId}
                onSelectNode={setSelectedNodeId}
                origins={origins}
              />
            )}
          </>
        )}
      </main>

      {selectedNode && activeTrace && (
        <NodeDetail
          node={selectedNode}
          trace={activeTrace}
          onClose={() => setSelectedNodeId(null)}
        />
      )}
    </div>
  );
}
