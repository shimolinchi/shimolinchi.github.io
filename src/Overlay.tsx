import { useStore } from "./store";
import { PANELS } from "./content";

// HTML 覆盖层：焦点在物体上时弹信息面板；全景时显示引导提示
export default function Overlay() {
  const focus = useStore((s) => s.focus);
  const hovered = useStore((s) => s.hovered);
  const setFocus = useStore((s) => s.setFocus);
  const panel = PANELS[focus];

  return (
    <div style={S.root}>
      {/* 顶部标题条 */}
      <div style={S.brand}>
        王锐 · shimolinchi
        <span style={S.brandSub}>点场景里的物体逛一逛 👀</span>
      </div>

      {/* 全景时的引导 */}
      {focus === "overview" && (
        <div style={S.hint}>
          {hovered ? `点一下 →「${labelOf(hovered)}」` : "把鼠标移到 脸 / 电脑 / 本子 / 工具架 上"}
        </div>
      )}

      {/* 信息面板 */}
      {panel && (
        <div style={S.panel} key={focus}>
          <div style={S.emoji}>{panel.emoji}</div>
          <h2 style={S.title}>{panel.title}</h2>
          <div style={S.subtitle}>{panel.subtitle}</div>
          <div style={S.body}>
            {panel.body.map((line, i) => (
              <p key={i} style={{ margin: "6px 0" }}>{line}</p>
            ))}
          </div>
          <button style={S.back} onClick={() => setFocus("overview")}>
            ← 回到全景
          </button>
        </div>
      )}
    </div>
  );
}

function labelOf(f: string) {
  return { person: "基本信息", computer: "算法项目", notebook: "论文", toolrack: "结构项目" }[f as keyof object] ?? f;
}

const S: Record<string, React.CSSProperties> = {
  root: { position: "fixed", inset: 0, pointerEvents: "none", zIndex: 10 },
  brand: {
    position: "absolute", top: 20, left: 22, color: "#4a2b12", fontWeight: 800,
    fontSize: 20, textShadow: "0 2px 0 #ffe9c7", display: "flex", flexDirection: "column",
  },
  brandSub: { fontSize: 12, fontWeight: 500, opacity: 0.75, marginTop: 2 },
  hint: {
    position: "absolute", bottom: 34, left: "50%", transform: "translateX(-50%)",
    background: "rgba(74,43,18,0.85)", color: "#fff", padding: "10px 18px",
    borderRadius: 999, fontSize: 14, fontWeight: 600, whiteSpace: "nowrap",
  },
  panel: {
    position: "absolute", top: "50%", right: "clamp(16px, 5vw, 60px)",
    transform: "translateY(-50%)", width: "min(340px, 82vw)",
    background: "rgba(255,255,255,0.95)", borderRadius: 22, padding: "26px 26px 20px",
    boxShadow: "0 18px 50px rgba(120,70,20,0.35)", pointerEvents: "auto",
    animation: "pop 0.35s cubic-bezier(0.18,1.4,0.4,1)",
  },
  emoji: { fontSize: 42, lineHeight: 1 },
  title: { margin: "8px 0 2px", fontSize: 22, color: "#2a1a0c" },
  subtitle: { fontSize: 13, color: "#b06a2c", fontWeight: 600, marginBottom: 12 },
  body: { fontSize: 14.5, color: "#3a3028", lineHeight: 1.55 },
  back: {
    marginTop: 16, border: "none", background: "#ff6f61", color: "#fff",
    padding: "9px 16px", borderRadius: 999, fontSize: 14, fontWeight: 700,
    cursor: "pointer", pointerEvents: "auto",
  },
};
