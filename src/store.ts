import { create } from "zustand";

// 四个可交互焦点 + 全景默认视角
export type Focus = "overview" | "person" | "computer" | "notebook" | "toolrack";

interface State {
  focus: Focus;
  hovered: Focus | null;
  setFocus: (f: Focus) => void;
  setHovered: (f: Focus | null) => void;
}

export const useStore = create<State>((set) => ({
  focus: "overview",
  hovered: null,
  setFocus: (focus) => set({ focus }),
  setHovered: (hovered) => set({ hovered }),
}));
