import type { Focus } from "./store";
import * as THREE from "three";

export interface CamShot {
  pos: THREE.Vector3;
  target: THREE.Vector3;
}

export const SHOTS: Record<Focus, CamShot> = {
  overview: { pos: new THREE.Vector3(6, 5, 8), target: new THREE.Vector3(0, 1.2, 0) },
  person: { pos: new THREE.Vector3(0.4, 2.4, 3.2), target: new THREE.Vector3(0, 2.3, -0.2) },
  computer: { pos: new THREE.Vector3(0, 2.2, 1.6), target: new THREE.Vector3(0, 1.7, -1.1) },
  notebook: { pos: new THREE.Vector3(-1.1, 2.6, 0.6), target: new THREE.Vector3(-1.1, 1.5, -0.6) },
  toolrack: { pos: new THREE.Vector3(3.2, 2.6, 0.8), target: new THREE.Vector3(2.95, 1.6, -1.45) },
  trophy: { pos: new THREE.Vector3(-2.5, 2.25, 0.15), target: new THREE.Vector3(-1.35, 1.62, -1.62) },
};

export interface Panel {
  emoji: string;
  title: string;
  subtitle: string;
  body: string[];
}

export const PANELS: Partial<Record<Focus, Panel>> = {
  person: {
    emoji: "🤖",
    title: "王锐 / shimolinchi",
    subtitle: "哈尔滨工业大学（深圳）· 机器人工程",
    body: [
      "本科毕业，已保送本校硕士研究生。",
      "关注灵巧操作、机器人学习与机电系统设计。",
      "技术栈：C/C++、Python、OpenCV、YOLO、ROS、Isaac Lab。",
    ],
  },
  computer: {
    emoji: "🖥️",
    title: "灵巧手视觉遥操作",
    subtitle: "视觉感知 · 动作映射 · 机器人部署",
    body: [
      "使用 RGB 相机与 MediaPipe 获取手部关键点并进行动作映射。",
      "结合 MANUS Glove 完成更精细的手部姿态采集。",
      "将 YOLO、AUBO 机械臂与 RY-16 灵巧手用于装配任务。",
    ],
  },
  notebook: {
    emoji: "📖",
    title: "论文与研究",
    subtitle: "一体化 3D 打印灵巧手",
    body: [
      "以第一作者完成 IROS 2026 灵巧手论文。",
      "负责机械设计、控制系统，并在 Isaac Lab 中开展 PPO 训练。",
      "围绕机器人机构与控制形成多项专利成果。",
    ],
  },
  toolrack: {
    emoji: "🛠️",
    title: "工程与竞赛",
    subtitle: "从机械设计到现场部署",
    body: [
      "获第二届珠海国际灵巧操作挑战赛生产赛道优胜奖。",
      "多次获得 VEX 亚洲赛、全国赛一等奖，并进入世锦赛十六强。",
      "具备机械设计、加工装配与机器人系统集成经验。",
    ],
  },
  trophy: {
    emoji: "🏆",
    title: "获奖经历",
    subtitle: "机器人竞赛与灵巧操作",
    body: [
      "第二届珠海国际灵巧操作挑战赛生产赛道优胜奖。",
      "多次获得 VEX 亚洲赛、全国赛一等奖。",
      "进入 VEX 世界锦标赛十六强，并获得多项机器人赛事奖项。",
    ],
  },
};
