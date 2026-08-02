import { GUIDED_FOCUSES, useStore, type ViewMode } from "./store";

const PRESET_LABELS = ["全景", "人物", "电脑", "笔记本", "奖杯", "工具架"];

function PinIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M8.2 3.8h7.6l-1.35 5.1 2.75 2.75v1.45H6.8v-1.45L9.55 8.9 8.2 3.8Z" />
      <path d="M12 13.1v7.1" />
    </svg>
  );
}

function FreeIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 12h16M7.5 8.5 4 12l3.5 3.5M16.5 8.5 20 12l-3.5 3.5" />
    </svg>
  );
}

export default function ViewModeControls() {
  const mode = useStore((state) => state.viewMode);
  const guidedIndex = useStore((state) => state.guidedIndex);
  const setViewMode = useStore((state) => state.setViewMode);
  const setGuidedIndex = useStore((state) => state.setGuidedIndex);

  const selectMode = (nextMode: ViewMode) => setViewMode(nextMode);

  return (
    <nav className="view-mode-controls" aria-label="视角模式">
      <div className={`guided-control ${mode === "guided" ? "is-active" : ""}`}>
        <button
          className={`mode-button ${mode === "guided" ? "is-active" : ""}`}
          type="button"
          aria-label="引导视角"
          aria-pressed={mode === "guided"}
          onClick={() => selectMode("guided")}
        >
          <PinIcon />
          <span>引导</span>
        </button>

        {mode === "guided" && (
          <div className="preset-dots" aria-label="预设视角">
            {GUIDED_FOCUSES.map((focus, index) => (
              <button
                key={focus}
                type="button"
                className={`preset-dot ${guidedIndex === index ? "is-current" : ""}`}
                aria-label={PRESET_LABELS[index]}
                aria-current={guidedIndex === index ? "true" : undefined}
                title={PRESET_LABELS[index]}
                onClick={() => setGuidedIndex(index)}
              />
            ))}
          </div>
        )}
      </div>

      <button
        className={`mode-button ${mode === "free" ? "is-active" : ""}`}
        type="button"
        aria-label="自由视角"
        aria-pressed={mode === "free"}
        onClick={() => selectMode("free")}
      >
        <FreeIcon />
        <span>自由</span>
      </button>
    </nav>
  );
}
