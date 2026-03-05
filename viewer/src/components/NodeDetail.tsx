import type { TraceGraph, TraceNode } from "../types/trace";
import { formatDuration, formatOffset, formatTimestamp } from "../lib/format";
import { StatusIndicator, TypeBadge } from "./NodeBadge";

interface Props {
  node: TraceNode;
  trace: TraceGraph;
  onClose: () => void;
}

function JsonBlock({ label, data }: { label: string; data: Record<string, unknown> }) {
  if (Object.keys(data).length === 0) return null;
  return (
    <div className="detail-section">
      <h4>{label}</h4>
      <pre className="json-block">{JSON.stringify(data, null, 2)}</pre>
    </div>
  );
}

export function NodeDetail({ node, trace, onClose }: Props) {
  const llmMeta = Object.entries(node.metadata).filter(([k]) => k.startsWith("llm."));
  const otherMeta = Object.entries(node.metadata).filter(([k]) => !k.startsWith("llm."));

  return (
    <aside className="node-detail">
      <div className="detail-header">
        <div className="detail-title-row">
          <StatusIndicator status={node.status} />
          <TypeBadge nodeType={node.node_type} />
          <h3>{node.name}</h3>
        </div>
        <button className="close-btn" onClick={onClose} title="Close">
          ✕
        </button>
      </div>

      <div className="detail-body">
        <div className="detail-section">
          <h4>Timing</h4>
          <div className="detail-grid">
            <span className="label">Offset</span>
            <span>{formatOffset(node.start_time, trace.start_time) || "—"}</span>
            <span className="label">Duration</span>
            <span>{formatDuration(node.duration_ms)}</span>
            <span className="label">Start</span>
            <span>{formatTimestamp(node.start_time)}</span>
            <span className="label">End</span>
            <span>{formatTimestamp(node.end_time)}</span>
          </div>
        </div>

        {node.annotations.length > 0 && (
          <div className="detail-section">
            <h4>Annotations</h4>
            <ul className="annotation-list">
              {node.annotations.map((a, i) => (
                <li key={i}>{a}</li>
              ))}
            </ul>
          </div>
        )}

        {node.error && (
          <div className="detail-section error-section">
            <h4>Error</h4>
            <div className="error-info">
              {node.error_type && <span className="error-type">{node.error_type}</span>}
              <span className="error-message">{node.error}</span>
            </div>
            {node.error_traceback && (
              <pre className="traceback">{node.error_traceback}</pre>
            )}
          </div>
        )}

        {llmMeta.length > 0 && (
          <div className="detail-section llm-section">
            <h4>LLM Details</h4>
            <div className="detail-grid">
              {llmMeta.map(([key, value]) => (
                <Fragment key={key}>
                  <span className="label">{key.replace("llm.", "")}</span>
                  <span>{String(value)}</span>
                </Fragment>
              ))}
            </div>
          </div>
        )}

        <JsonBlock label="Input" data={node.input_data} />
        <JsonBlock label="Output" data={node.output_data} />

        {otherMeta.length > 0 && (
          <div className="detail-section">
            <h4>Metadata</h4>
            <pre className="json-block">
              {JSON.stringify(Object.fromEntries(otherMeta), null, 2)}
            </pre>
          </div>
        )}
      </div>
    </aside>
  );
}

function Fragment({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
