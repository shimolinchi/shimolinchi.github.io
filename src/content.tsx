import type { Focus } from "./store";
import * as THREE from "three";

// 每个焦点对应的相机机位（位置 + 看向的目标点）
export interface CamShot {
  pos: THREE.Vector3;
  target: THREE.Vector3;
}

export const SHOTS: Record<Focus, CamShot> = {
  overview: { pos: new THREE.Vector3(6, 5, 8), target: new THREE.Vector3(0, 1.2, 0) },
  person: { pos: new THREE.Vector3(0.4, 2.4, 3.2), target: new THREE.Vector3(0, 2.3, -0.2) },
  computer: { pos: new THREE.Vector3(0, 2.2, 1.6), target: new THREE.Vector3(0, 1.7, -1.1) },
  notebook: { pos: new THREE.Vector3(-1.1, 2.6, 0.6), target: new THREE.Vector3(-1.1, 1.5, -0.6) },
  toolrack: { pos: new THREE.Vector3(2.6, 2.6, 0.8), target: new THREE.Vector3(2.6, 1.8, -1.4) },
};

// 信息面板内容 —— 占位文案，你之后随便改
export interface Panel {
  emoji: string;
  title: string;
  subtitle: string;
  body: string[];
}

export const PANELS: Partial<Record<Focus, Panel>> = {
  person: {
    emoji: "🧑‍💻",
    title: "王锐 / shimolinchi",
    subtitle: "点我的脸 → 基本信息",
    body: [
      "机器人 / 算法方向，爱折腾。",
      "邮箱：2226187480@qq.com",
      "座右铭：试墨临池，事莫临迟。",
      "（这里的文案都是占位，随便改）",
    ],
  },
  computer: {
    emoji: "💻",
    title: "算法项目",
    subtitle: "点电脑 → 我写过的算法",
    body: [
      "· 项目一：占位标题，一句话简介。",
      "· 项目二：占位标题，一句话简介。",
      "· 项目三：占位标题，一句话简介。",
    ],
  },
  notebook: {
    emoji: "📓",
    title: "论文",
    subtitle: "点本子 → 我的论文",
    body: [
      "· 论文一：标题 / 会议或期刊 / 年份。",
      "· 论文二：标题 / 会议或期刊 / 年份。",
    ],
  },
  toolrack: {
    emoji: "🔧",
    title: "结构项目",
    subtitle: "点工具架 → 我的结构设计",
    body: [
      "· 结构项目一：占位标题。",
      "· 结构项目二：占位标题。",
    ],
  },
};
