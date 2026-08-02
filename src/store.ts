import { create } from "zustand";

export type Focus = "overview" | "person" | "computer" | "notebook" | "trophy" | "toolrack";
export type ViewMode = "guided" | "free";
export type GuidedTransitionStage =
  | "idle"
  | "person-to-computer-before"
  | "person-to-computer-after"
  | "computer-to-person-before"
  | "computer-to-person-after";

export const GUIDED_FOCUSES: Focus[] = [
  "overview",
  "person",
  "computer",
  "notebook",
  "trophy",
  "toolrack",
];

interface State {
  focus: Focus;
  hovered: Focus | null;
  viewMode: ViewMode;
  guidedIndex: number;
  panelRequestId: number;
  guidedTransitionStage: GuidedTransitionStage;
  setFocus: (focus: Focus) => void;
  setHovered: (focus: Focus | null) => void;
  setViewMode: (mode: ViewMode) => void;
  setGuidedIndex: (index: number) => void;
  setGuidedTransitionStage: (stage: GuidedTransitionStage) => void;
}

export const useStore = create<State>((set) => ({
  focus: "person",
  hovered: null,
  viewMode: "guided",
  guidedIndex: 1,
  panelRequestId: 0,
  guidedTransitionStage: "idle",
  setFocus: (focus) =>
    set((state) => {
      const index = GUIDED_FOCUSES.indexOf(focus);
      return {
        focus,
        panelRequestId: state.panelRequestId + 1,
        guidedIndex: index >= 0 ? index : state.guidedIndex,
        guidedTransitionStage:
          state.viewMode === "guided" && state.guidedIndex === 1 && index === 2
            ? "person-to-computer-before"
            : state.viewMode === "guided" && state.guidedIndex === 2 && index === 1
              ? "computer-to-person-before"
              : "idle",
      };
    }),
  setHovered: (hovered) => set({ hovered }),
  setViewMode: (viewMode) => set({ viewMode }),
  setGuidedIndex: (index) => {
    const guidedIndex = Math.max(0, Math.min(GUIDED_FOCUSES.length - 1, index));
    set((state) => ({
      guidedIndex,
      focus: GUIDED_FOCUSES[guidedIndex],
      guidedTransitionStage:
        state.guidedIndex === 1 && guidedIndex === 2
          ? "person-to-computer-before"
          : state.guidedIndex === 2 && guidedIndex === 1
            ? "computer-to-person-before"
            : "idle",
    }));
  },
  setGuidedTransitionStage: (guidedTransitionStage) => set({ guidedTransitionStage }),
}));
