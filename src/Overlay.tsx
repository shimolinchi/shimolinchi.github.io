import { PANELS } from "./content";
import { useStore, type Focus } from "./store";
import ViewModeControls from "./ViewModeControls";
import { useEffect, useState } from "react";

export default function Overlay() {
  const [panelMode, setPanelMode] = useState<"rail" | "fullscreen" | "collapsed">("rail");
  const focus = useStore((state) => state.focus);
  const hovered = useStore((state) => state.hovered);
  const viewMode = useStore((state) => state.viewMode);
  const panelRequestId = useStore((state) => state.panelRequestId);
  const setFocus = useStore((state) => state.setFocus);
  const panel = PANELS[focus];

  useEffect(() => {
    if (focus !== "overview") setPanelMode("rail");
  }, [focus, panelRequestId]);

  return (
    <div className="overlay-root">
      <div className="brand-block">
        王锐 · shimolinchi
        <span>探索我的机器人工作空间</span>
      </div>

      <ViewModeControls />

      {focus === "overview" && (
        <div className="scene-hint">
          {hovered
            ? `点击查看：${labelOf(hovered)}`
            : viewMode === "guided"
              ? "上下滚动 · 切换预设视角"
              : "中键旋转 · 滚轮缩放 · 拖动平移"}
        </div>
      )}

      {panel && (
        <article className={`info-panel is-${panelMode}`} key={focus}>
          <button
            className="panel-toggle"
            type="button"
            aria-label={panelMode === "fullscreen" ? "退出全屏介绍" : "展开全屏介绍"}
            aria-expanded={panelMode === "fullscreen"}
            onClick={() => setPanelMode(panelMode === "fullscreen" ? "rail" : "fullscreen")}
          >
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M15 5 8 12l7 7" />
            </svg>
          </button>
          <button
            className="panel-collapse-toggle"
            type="button"
            aria-label={panelMode === "collapsed" ? "恢复介绍栏" : "收回介绍栏"}
            aria-expanded={panelMode !== "collapsed"}
            onClick={() => setPanelMode(panelMode === "collapsed" ? "rail" : "collapsed")}
          >
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="m9 5 7 7-7 7" />
            </svg>
          </button>
          <div className="panel-content">
            <header className="panel-header">
              <div className="panel-title-row">
                <span className="panel-emoji" aria-hidden="true">{panel.emoji}</span>
                <h2>{panel.title}</h2>
              </div>
              <div className="panel-subtitle">{panel.subtitle}</div>
            </header>
            <div className="panel-body">
              {panel.items.map((item, index) => (
                <div className="panel-point" key={index}>
                  <span className="panel-point-index">{String(index + 1).padStart(2, "0")}</span>
                  <div className="panel-point-content">
                    {item.date && <span className="panel-point-date">{item.date}</span>}
                    <h3>{item.title}</h3>
                    {item.description && <p>{item.description}</p>}
                    {item.href && (
                      <a href={item.href} target="_blank" rel="noreferrer">
                        {item.linkLabel ?? "查看详情"}
                        <span aria-hidden="true">↗</span>
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </article>
      )}
    </div>
  );
}

function labelOf(focus: Focus) {
  const labels: Record<Focus, string> = {
    overview: "全景",
    person: "个人信息",
    computer: "视觉遥操作",
    notebook: "论文与研究",
    trophy: "获奖经历",
    toolrack: "工程项目",
  };
  return labels[focus];
}
