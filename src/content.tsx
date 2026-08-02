import type { Focus } from "./store";
import * as THREE from "three";

export interface CamShot {
  pos: THREE.Vector3;
  target: THREE.Vector3;
}

export const SHOTS: Record<Focus, CamShot> = {
  overview: { pos: new THREE.Vector3(-6, 5, 8), target: new THREE.Vector3(0, 1.2, -0.35) },
  person: { pos: new THREE.Vector3(0.15, 2.45, -2.65), target: new THREE.Vector3(0, 2.15, -0.05) },
  computer: { pos: new THREE.Vector3(0, 2.12, 0.82), target: new THREE.Vector3(0, 1.78, -1.0) },
  notebook: { pos: new THREE.Vector3(-1.1, 2.6, 0.6), target: new THREE.Vector3(-1.1, 1.5, -0.6) },
  toolrack: { pos: new THREE.Vector3(-3.2, 2.6, 0.8), target: new THREE.Vector3(-2.95, 1.6, -1.45) },
  trophy: { pos: new THREE.Vector3(-2.5, 2.25, 0.15), target: new THREE.Vector3(-1.35, 1.62, -1.62) },
};

export interface PanelItem {
  date?: string;
  title: string;
  description?: string;
  href?: string;
  linkLabel?: string;
}

export interface Panel {
  emoji: string;
  title: string;
  subtitle: string;
  items: PanelItem[];
}

const searchLink = (query: string) =>
  `https://www.google.com/search?q=${encodeURIComponent(query)}`;

export const PANELS: Partial<Record<Focus, Panel>> = {
  person: {
    emoji: "🤖",
    title: "王锐 / shimolinchi",
    subtitle: "机器人工程 · 灵巧操作 · 机器人学习",
    items: [
      { date: "教育背景", title: "哈尔滨工业大学（深圳）", description: "机器人工程专业本科毕业，已保送本校硕士研究生。关注机器人机构、感知、控制与学习方法的交叉研究。", href: "https://www.hitsz.edu.cn/", linkLabel: "学校官网" },
      { date: "研究方向", title: "面向真实任务的灵巧机器人", description: "研究灵巧手结构设计、视觉与手套遥操作、动作映射，以及基于强化学习的手内操作。", href: "https://github.com/shimolinchi", linkLabel: "GitHub" },
      { date: "2025.08-2025.12", title: "算法实习 · 机器人遥操作", description: "参与视觉识别与灵巧手遥操作算法研发，将 MediaPipe、MANUS Glove、YOLO、AUBO 机械臂和 RY-16 灵巧手应用于真实装配任务。", href: "https://github.com/shimolinchi", linkLabel: "项目主页" },
      { date: "技术能力", title: "软件、算法与工程实现", description: "使用 C/C++、Python、Git、Linux 与 Docker；熟悉 OpenCV、YOLO、ROS、Isaac Lab，并具备机械设计、加工装配和机器人系统集成经验。", href: "https://github.com/shimolinchi", linkLabel: "查看代码" },
      { date: "科研与竞赛", title: "从原型设计到现场部署", description: "以第一作者完成 IROS 2026 灵巧手论文，形成多项发明专利；曾获机器人赛事全国一等奖、亚洲赛事奖项及国际灵巧操作挑战赛优胜奖。", href: searchLink("shimolinchi 王锐 机器人"), linkLabel: "了解更多" },
    ],
  },
  computer: {
    emoji: "🖥️",
    title: "算法项目",
    subtitle: "视觉感知 · 动作映射 · 强化学习",
    items: [
      { date: "2025", title: "MediaPipe 视觉遥操作", description: "基于 RGB 相机提取手部关键点，并映射到 RY-16 灵巧手关节。", href: searchLink("MediaPipe hand landmarks robotic hand teleoperation"), linkLabel: "相关技术" },
      { date: "2025", title: "MANUS Glove 动作映射", description: "完成手部姿态采集、数据滤波、动作映射与实时控制。", href: "https://www.manus-meta.com/", linkLabel: "MANUS" },
      { date: "2025-2026", title: "Isaac Lab 灵巧手强化学习", description: "搭建方块旋转任务，并使用 PPO 训练灵巧手完成姿态调整。", href: "https://isaac-sim.github.io/IsaacLab/", linkLabel: "Isaac Lab" },
      { date: "2025", title: "YOLO 机器人装配系统", description: "结合 YOLO、AUBO 机械臂与 RY-16 灵巧手完成装配任务。", href: "https://github.com/ultralytics/ultralytics", linkLabel: "YOLO" },
    ],
  },
  notebook: {
    emoji: "📖",
    title: "论文与专利",
    subtitle: "灵巧手结构、传动与机器人感知",
    items: [
      { date: "IROS 2026", title: "Design of an Integrated 3D-Printed Hand with Variable Cross-Section Tendon Transmission for Dexterous Manipulation", description: "第一作者论文。", href: searchLink("Design of an Integrated 3D-Printed Hand with Variable Cross-Section Tendon Transmission for Dexterous Manipulation"), linkLabel: "检索论文" },
      { date: "CN117104334A", title: "一种差动手指夹小球", description: "发明专利。", href: "https://patents.google.com/patent/CN117104334A/zh", linkLabel: "查看专利" },
      { date: "CN121505241A", title: "基于双路扩散的多模态大模型具身感知与控制系统", description: "发明专利。", href: "https://patents.google.com/patent/CN121505241A/zh", linkLabel: "查看专利" },
      { date: "202610548541.0", title: "一种一体化 3D 打印灵巧手指及运动学建模方法", description: "发明专利申请。", href: searchLink("202610548541.0 专利"), linkLabel: "检索专利" },
      { date: "202610548369.9", title: "一种基于变截面肌腱传动的 3D 打印手指机构", description: "发明专利申请。", href: searchLink("202610548369.9 专利"), linkLabel: "检索专利" },
    ],
  },
  trophy: {
    emoji: "🏆",
    title: "获奖经历",
    subtitle: "机器人竞赛 · 科技创新 · 综合荣誉",
    items: [
      { date: "2026", title: "VEX 世界锦标赛参赛资格", href: "https://www.vexrobotics.com/competition", linkLabel: "赛事官网" },
      { date: "2025", title: "第十九届“挑战杯”全国大学生课外学术科技作品竞赛“人工智能+”专项赛二等奖", href: searchLink("第十九届 挑战杯 人工智能+ 专项赛"), linkLabel: "查看赛事" },
      { date: "2025", title: "第二届珠海国际灵巧操作挑战赛生产赛道优胜奖", href: searchLink("第二届珠海国际灵巧操作挑战赛 生产赛道"), linkLabel: "查看赛事" },
      { date: "2024", title: "VEX 世界锦标赛十六强", href: "https://www.vexrobotics.com/competition", linkLabel: "赛事官网" },
      { date: "2024", title: "第七届中国高校智能机器人创意大赛全国一等奖、最佳创意奖", href: searchLink("第七届 中国高校智能机器人创意大赛"), linkLabel: "查看赛事" },
      { date: "2023-2024", title: "VEX 亚洲公开赛大学组第二名", href: "https://www.robotevents.com/", linkLabel: "赛事平台" },
      { date: "2023-2024", title: "全国 VEX 机器人精英赛大学组一等奖", href: "https://www.robotevents.com/", linkLabel: "赛事平台" },
      { date: "2023-2024", title: "VEX 亚洲锦标赛技能赛冠军", href: "https://www.robotevents.com/", linkLabel: "赛事平台" },
      { date: "2023", title: "中国高校智能机器人创意大赛全国一等奖、最佳创意奖", href: searchLink("2023 中国高校智能机器人创意大赛"), linkLabel: "查看赛事" },
      { date: "2023-2024", title: "校优秀奖学金", href: "https://www.hitsz.edu.cn/", linkLabel: "学校官网" },
    ],
  },
  toolrack: {
    emoji: "🛠️",
    title: "结构项目",
    subtitle: "机械设计 · 加工装配 · 系统集成",
    items: [
      { date: "2025-2026", title: "一体化 3D 打印灵巧手", description: "负责手指结构设计、参数优化、加工装配与结构测试。", href: searchLink("integrated 3D printed dexterous hand tendon transmission"), linkLabel: "相关研究" },
      { date: "2025", title: "RY-16 灵巧手遥操作平台", description: "参与灵巧手本体、传感器与控制系统的集成和现场调试。", href: "https://github.com/shimolinchi", linkLabel: "GitHub" },
      { date: "2025", title: "机器人自动装配实验平台", description: "集成 AUBO 机械臂、灵巧手和视觉系统，完成夹持与装配流程。", href: "https://www.aubo-robotics.cn/", linkLabel: "AUBO" },
      { date: "2022-2024", title: "VEX 竞赛机器人", description: "参与竞赛机器人机械结构设计、加工装配和系统调试。", href: "https://www.vexrobotics.com/competition", linkLabel: "赛事官网" },
    ],
  },
};
