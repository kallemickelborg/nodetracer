export type ViewMode = "tree" | "timeline" | "graph";

interface Props {
  mode: ViewMode;
  onChange: (mode: ViewMode) => void;
}

export function ViewToggle({ mode, onChange }: Props) {
  return (
    <div className="view-toggle">
      <button
        className={`view-toggle-btn ${mode === "tree" ? "active" : ""}`}
        onClick={() => onChange("tree")}
      >
        Tree
      </button>
      <button
        className={`view-toggle-btn ${mode === "timeline" ? "active" : ""}`}
        onClick={() => onChange("timeline")}
      >
        Timeline
      </button>
      <button
        className={`view-toggle-btn ${mode === "graph" ? "active" : ""}`}
        onClick={() => onChange("graph")}
      >
        Graph
      </button>
    </div>
  );
}
