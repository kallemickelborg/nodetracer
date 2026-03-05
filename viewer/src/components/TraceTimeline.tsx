import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { TraceGraph, TraceNode } from "../types/trace";
import {
  getNodeTypeColor,
  STATUS_COLORS,
  getEdgeStyle,
  getTraceAccentColor,
} from "../lib/colors";
import { formatDuration, formatOffset } from "../lib/format";
import {
  computeSwimlanes,
  createTimeScale,
  computeLaneLayouts,
  computeBarPositions,
  computeDropLines,
  computeEdgePaths,
  computeTimeAxis,
  getTotalHeight,
  HEADER_HEIGHT,
  BAR_HEIGHT,
  type BarRect,
  type EdgePath,
} from "../lib/timeline";
import type { TraceOriginMap } from "../lib/merge";
import type { TimeMode } from "../App";

interface Props {
  trace: TraceGraph;
  selectedNodeId: string | null;
  onSelectNode: (nodeId: string) => void;
  origins?: TraceOriginMap | null;
  timeMode?: TimeMode;
  onTimeModeChange?: (mode: TimeMode) => void;
}

const LABEL_WIDTH = 110;

interface TooltipState {
  x: number;
  y: number;
  node?: TraceNode;
  edgePath?: EdgePath;
}

const MIN_ZOOM = 1;
const MAX_ZOOM = 10;
const ZOOM_STEP = 0.25;

export function TraceTimeline({
  trace,
  selectedNodeId,
  onSelectNode,
  origins,
  timeMode,
  onTimeModeChange,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [baseWidth, setBaseWidth] = useState(600);
  const [zoom, setZoom] = useState(1);
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);
  const [hoveredEdgeIdx, setHoveredEdgeIdx] = useState<number | null>(null);

  const chartWidth = Math.round(baseWidth * zoom);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width ?? 600;
      setBaseWidth(Math.max(200, w - LABEL_WIDTH));
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    const scrollEl = scrollRef.current;
    if (!scrollEl) return;
    const handleWheel = (e: WheelEvent) => {
      if (!e.ctrlKey && !e.metaKey) return;
      e.preventDefault();
      const delta = e.deltaY > 0 ? -ZOOM_STEP : ZOOM_STEP;
      setZoom((prev) => Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, prev + delta)));
    };
    scrollEl.addEventListener("wheel", handleWheel, { passive: false });
    return () => scrollEl.removeEventListener("wheel", handleWheel);
  }, []);

  const handleZoomIn = useCallback(() => {
    setZoom((prev) => Math.min(MAX_ZOOM, prev + ZOOM_STEP));
  }, []);

  const handleZoomOut = useCallback(() => {
    setZoom((prev) => Math.max(MIN_ZOOM, prev - ZOOM_STEP));
  }, []);

  const handleZoomReset = useCallback(() => {
    setZoom(1);
  }, []);

  const lanes = useMemo(() => computeSwimlanes(trace), [trace]);
  const scale = useMemo(
    () => createTimeScale(trace, chartWidth, LABEL_WIDTH),
    [trace, chartWidth],
  );

  const laneLayouts = useMemo(
    () => (scale ? computeLaneLayouts(trace, lanes, scale) : []),
    [trace, lanes, scale],
  );

  const bars = useMemo(
    () => (scale ? computeBarPositions(trace, lanes, scale, laneLayouts) : new Map<string, BarRect>()),
    [trace, lanes, scale, laneLayouts],
  );

  const dropLines = useMemo(() => computeDropLines(trace, bars), [trace, bars]);
  const edgePaths = useMemo(() => computeEdgePaths(trace, bars), [trace, bars]);
  const ticks = useMemo(() => (scale ? computeTimeAxis(scale) : []), [scale]);

  const totalHeight = getTotalHeight(laneLayouts);
  const svgWidth = LABEL_WIDTH + chartWidth;

  const isMultiTrace = origins != null && origins.traceOrder.length > 1;

  const handleBarMouseEnter = useCallback(
    (e: React.MouseEvent, node: TraceNode) => {
      const rect = containerRef.current?.getBoundingClientRect();
      if (!rect) return;
      setTooltip({
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
        node,
      });
    },
    [],
  );

  const handleEdgeMouseEnter = useCallback(
    (e: React.MouseEvent, ep: EdgePath, idx: number) => {
      const rect = containerRef.current?.getBoundingClientRect();
      if (!rect) return;
      setHoveredEdgeIdx(idx);
      setTooltip({
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
        edgePath: ep,
      });
    },
    [],
  );

  const handleMouseLeave = useCallback(() => {
    setTooltip(null);
    setHoveredEdgeIdx(null);
  }, []);

  if (!scale) {
    return (
      <div className="trace-timeline-empty">
        No timing data available for this trace.
      </div>
    );
  }

  return (
    <div className="trace-timeline" ref={containerRef}>
      <div className="timeline-toolbar">
        <div className="toolbar-left">
          <div className="zoom-controls">
            <button
              className="zoom-btn"
              onClick={handleZoomOut}
              disabled={zoom <= MIN_ZOOM}
              title="Zoom out"
            >
              −
            </button>
            <button
              className="zoom-label"
              onClick={handleZoomReset}
              title="Reset zoom"
            >
              {Math.round(zoom * 100)}%
            </button>
            <button
              className="zoom-btn"
              onClick={handleZoomIn}
              disabled={zoom >= MAX_ZOOM}
              title="Zoom in"
            >
              +
            </button>
          </div>

          {onTimeModeChange && (
            <div className="time-mode-toggle">
              <button
                className={`time-mode-btn ${timeMode === "absolute" ? "active" : ""}`}
                onClick={() => onTimeModeChange("absolute")}
              >
                Absolute
              </button>
              <button
                className={`time-mode-btn ${timeMode === "normalized" ? "active" : ""}`}
                onClick={() => onTimeModeChange("normalized")}
              >
                Normalized
              </button>
            </div>
          )}
        </div>
        <span className="zoom-hint">Ctrl+Scroll to zoom</span>
      </div>

      {isMultiTrace && origins && (
        <TraceLegend origins={origins} />
      )}

      <div className="timeline-scroll" ref={scrollRef}>
        <svg
          width={svgWidth}
          height={totalHeight}
          className="timeline-svg"
        >
          <defs>
            <marker
              id="arrowhead"
              markerWidth="8"
              markerHeight="6"
              refX="7"
              refY="3"
              orient="auto"
            >
              <polygon points="0 0, 8 3, 0 6" fill="currentColor" />
            </marker>
          </defs>

          {/* Time axis ticks */}
          {ticks.map((tick, i) => (
            <g key={i}>
              <line
                x1={tick.x}
                y1={HEADER_HEIGHT - 4}
                x2={tick.x}
                y2={totalHeight}
                stroke="var(--border)"
                strokeWidth={1}
                strokeDasharray={tick.ms === 0 ? "" : "2 4"}
                opacity={0.5}
              />
              <text
                x={tick.x}
                y={HEADER_HEIGHT - 8}
                fill="var(--text-muted)"
                fontSize={10}
                textAnchor="middle"
                fontFamily="var(--font-mono)"
              >
                {tick.label}
              </text>
            </g>
          ))}

          {/* Swimlane backgrounds */}
          {laneLayouts.map((layout, i) => (
            <rect
              key={layout.lane}
              x={0}
              y={layout.yStart}
              width={svgWidth}
              height={layout.totalHeight}
              fill={i % 2 === 0 ? "var(--bg-secondary)" : "var(--bg-tertiary)"}
              rx={2}
            />
          ))}

          {/* Swimlane labels */}
          {laneLayouts.map((layout) => (
            <text
              key={`label-${layout.lane}`}
              x={8}
              y={layout.yStart + layout.totalHeight / 2}
              fill="var(--text-secondary)"
              fontSize={11}
              fontFamily="var(--font-mono)"
              dominantBaseline="central"
            >
              {layout.lane}
            </text>
          ))}

          {/* Parent-child drop-lines */}
          {dropLines.map((dl, i) => (
            <line
              key={`drop-${i}`}
              x1={dl.x}
              y1={dl.y1}
              x2={dl.x}
              y2={dl.y2}
              stroke="#64748b"
              strokeWidth={1}
              opacity={0.45}
              strokeDasharray="3 2"
            />
          ))}

          {/* Edge paths */}
          {edgePaths.map((ep, i) => {
            const style = getEdgeStyle(ep.edge.edge_type);
            const isHovered = hoveredEdgeIdx === i;
            return (
              <g key={`edge-${i}`}>
                <path
                  d={ep.d}
                  fill="none"
                  stroke="transparent"
                  strokeWidth={12}
                  onMouseEnter={(e) => handleEdgeMouseEnter(e, ep, i)}
                  onMouseLeave={handleMouseLeave}
                  style={{ cursor: "pointer" }}
                />
                <path
                  d={ep.d}
                  fill="none"
                  stroke={style.color}
                  strokeWidth={isHovered ? 2.5 : 1.5}
                  strokeDasharray={style.dashArray}
                  opacity={isHovered ? 1 : 0.6}
                  markerEnd="url(#arrowhead)"
                  color={style.color}
                  className="timeline-edge"
                  pointerEvents="none"
                />
              </g>
            );
          })}

          {/* Bar clip paths */}
          {Array.from(bars.entries()).map(([nodeId, bar]) => (
            <clipPath key={`clip-${nodeId}`} id={`clip-${nodeId}`}>
              <rect x={bar.x + 6} y={bar.y} width={Math.max(0, bar.width - 10)} height={bar.height} />
            </clipPath>
          ))}

          {/* Bars */}
          {Array.from(bars.entries()).map(([nodeId, bar]) => {
            const node = trace.nodes[nodeId];
            if (!node) return null;
            const typeColor = getNodeTypeColor(node.node_type);
            const isSelected = selectedNodeId === nodeId;
            const isFailed = node.status === "failed";
            const barTextFits = bar.width > 50;

            const accentColor = getBarAccentColor(nodeId, origins);

            return (
              <g
                key={nodeId}
                className="timeline-bar-group"
                onClick={() => onSelectNode(nodeId)}
                onMouseEnter={(e) => handleBarMouseEnter(e, node)}
                onMouseLeave={handleMouseLeave}
                style={{ cursor: "pointer" }}
              >
                {bar.width < 12 && (
                  <rect
                    x={bar.x - 4}
                    y={bar.y}
                    width={bar.width + 8}
                    height={bar.height}
                    fill="transparent"
                  />
                )}
                <rect
                  x={bar.x}
                  y={bar.y}
                  width={bar.width}
                  height={bar.height}
                  rx={4}
                  fill={typeColor}
                  fillOpacity={node.status === "pending" ? 0.15 : 0.25}
                  stroke={isFailed ? STATUS_COLORS.failed : isSelected ? "var(--accent)" : typeColor}
                  strokeWidth={isSelected ? 2 : 1}
                  strokeOpacity={isFailed ? 0.9 : isSelected ? 1 : 0.6}
                  strokeDasharray={node.status === "pending" ? "4 2" : ""}
                />
                {/* Left accent border — trace color when multi-trace, node type otherwise */}
                <rect
                  x={bar.x}
                  y={bar.y}
                  width={3}
                  height={bar.height}
                  rx={1.5}
                  fill={accentColor}
                  fillOpacity={0.9}
                />
                {barTextFits && (
                  <text
                    x={bar.x + 8}
                    y={bar.y + BAR_HEIGHT / 2}
                    fill="var(--text-primary)"
                    fontSize={10}
                    fontFamily="var(--font-mono)"
                    dominantBaseline="central"
                    clipPath={`url(#clip-${nodeId})`}
                  >
                    {node.name}
                  </text>
                )}
                {isFailed && (
                  <text
                    x={bar.x + bar.width - 12}
                    y={bar.y + BAR_HEIGHT / 2}
                    fill={STATUS_COLORS.failed}
                    fontSize={12}
                    dominantBaseline="central"
                    textAnchor="middle"
                  >
                    ✗
                  </text>
                )}
              </g>
            );
          })}
        </svg>

        {tooltip && (
          <TimelineTooltip tooltip={tooltip} trace={trace} origins={origins} />
        )}
      </div>
    </div>
  );
}

function getBarAccentColor(
  nodeId: string,
  origins: TraceOriginMap | null | undefined,
): string {
  if (!origins) return "currentColor";
  const traceId = origins.nodeToTrace.get(nodeId);
  if (!traceId) return "currentColor";
  const idx = origins.traceOrder.indexOf(traceId);
  return idx >= 0 ? getTraceAccentColor(idx) : "currentColor";
}

function TraceLegend({ origins }: { origins: TraceOriginMap }) {
  return (
    <div className="trace-legend">
      {origins.traceOrder.map((traceId, i) => (
        <div key={traceId} className="trace-legend-item">
          <span
            className="trace-legend-swatch"
            style={{ background: getTraceAccentColor(i) }}
          />
          <span className="trace-legend-name">
            {origins.traceNames.get(traceId) ?? traceId}
          </span>
        </div>
      ))}
    </div>
  );
}

function TimelineTooltip({
  tooltip,
  trace,
  origins,
}: {
  tooltip: TooltipState;
  trace: TraceGraph;
  origins?: TraceOriginMap | null;
}) {
  const offsetX = 12;
  const offsetY = -8;

  if (tooltip.node) {
    const node = tooltip.node;
    const traceName = origins?.nodeToTrace.get(node.id)
      ? origins.traceNames.get(origins.nodeToTrace.get(node.id)!)
      : undefined;

    return (
      <div
        className="timeline-tooltip"
        style={{
          left: tooltip.x + offsetX,
          top: tooltip.y + offsetY,
        }}
      >
        <div className="timeline-tooltip-title">{node.name}</div>
        {traceName && (
          <div className="timeline-tooltip-row">
            <span className="timeline-tooltip-label">Trace</span>
            <span className="timeline-tooltip-value">{traceName}</span>
          </div>
        )}
        <div className="timeline-tooltip-row">
          <span className="timeline-tooltip-label">Type</span>
          <span
            className="timeline-tooltip-value"
            style={{ color: getNodeTypeColor(node.node_type) }}
          >
            {node.node_type}
          </span>
        </div>
        <div className="timeline-tooltip-row">
          <span className="timeline-tooltip-label">Status</span>
          <span
            className="timeline-tooltip-value"
            style={{ color: STATUS_COLORS[node.status] }}
          >
            {node.status}
          </span>
        </div>
        <div className="timeline-tooltip-row">
          <span className="timeline-tooltip-label">Offset</span>
          <span className="timeline-tooltip-value">
            {formatOffset(node.start_time, trace.start_time)}
          </span>
        </div>
        <div className="timeline-tooltip-row">
          <span className="timeline-tooltip-label">Duration</span>
          <span className="timeline-tooltip-value">
            {formatDuration(node.duration_ms)}
          </span>
        </div>
        {node.error && (
          <div className="timeline-tooltip-error">{node.error}</div>
        )}
      </div>
    );
  }

  if (tooltip.edgePath) {
    const ep = tooltip.edgePath;
    const style = getEdgeStyle(ep.edge.edge_type);
    const sourceNode = trace.nodes[ep.edge.source_id];
    const targetNode = trace.nodes[ep.edge.target_id];
    return (
      <div
        className="timeline-tooltip"
        style={{
          left: tooltip.x + offsetX,
          top: tooltip.y + offsetY,
        }}
      >
        <div className="timeline-tooltip-title" style={{ color: style.color }}>
          {style.label}
        </div>
        <div className="timeline-tooltip-row">
          <span className="timeline-tooltip-label">From</span>
          <span className="timeline-tooltip-value">
            {sourceNode?.name ?? ep.edge.source_id}
          </span>
        </div>
        <div className="timeline-tooltip-row">
          <span className="timeline-tooltip-label">To</span>
          <span className="timeline-tooltip-value">
            {targetNode?.name ?? ep.edge.target_id}
          </span>
        </div>
      </div>
    );
  }

  return null;
}
