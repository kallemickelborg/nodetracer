import { getNodeTypeColor, STATUS_COLORS, STATUS_ICONS } from "../lib/colors";
import type { NodeStatus } from "../types/trace";

interface TypeBadgeProps {
  nodeType: string;
}

export function TypeBadge({ nodeType }: TypeBadgeProps) {
  const color = getNodeTypeColor(nodeType);
  return (
    <span className="node-type-badge" style={{ backgroundColor: color }}>
      {nodeType}
    </span>
  );
}

interface StatusIndicatorProps {
  status: NodeStatus;
}

export function StatusIndicator({ status }: StatusIndicatorProps) {
  const color = STATUS_COLORS[status];
  const icon = STATUS_ICONS[status];
  return (
    <span className="status-indicator" style={{ color }} title={status}>
      {icon}
    </span>
  );
}
