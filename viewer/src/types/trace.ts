export type NodeStatus = "pending" | "running" | "completed" | "failed" | "cancelled";

export interface TraceNode {
  id: string;
  sequence_number: number;
  name: string;
  node_type: string;
  status: NodeStatus;
  parent_id: string | null;
  depth: number;
  start_time: string | null;
  end_time: string | null;
  input_data: Record<string, unknown>;
  output_data: Record<string, unknown>;
  annotations: string[];
  metadata: Record<string, unknown>;
  error: string | null;
  error_type: string | null;
  error_traceback: string | null;
  duration_ms: number | null;
}

export interface Edge {
  source_id: string;
  target_id: string;
  edge_type: string;
}

export interface TraceGraph {
  schema_version: string;
  trace_id: string;
  name: string;
  nodes: Record<string, TraceNode>;
  edges: Edge[];
  start_time: string | null;
  end_time: string | null;
  duration_ms: number | null;
  metadata: Record<string, unknown>;
}

export interface TraceSummary {
  id: string;
  name: string;
  duration_ms: number | null;
  start_time: string | null;
  node_count: number;
  edge_count: number;
  error?: string;
  session_id?: string | null;
}
