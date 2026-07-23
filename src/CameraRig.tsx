import { useFrame, useThree } from "@react-three/fiber";
import { useRef } from "react";
import * as THREE from "three";
import { useStore } from "./store";
import { SHOTS } from "./content";

// 相机在预设机位之间平滑插值飞行；overview 时轻微环绕漂浮
export default function CameraRig() {
  const { camera } = useThree();
  const focus = useStore((s) => s.focus);
  const curTarget = useRef(new THREE.Vector3(0, 1.2, 0));

  useFrame((_, dt) => {
    const shot = SHOTS[focus];
    const k = 1 - Math.pow(0.0015, dt); // 帧率无关的平滑系数

    // 相机固定停在每个焦点的机位，不自动转动
    camera.position.lerp(shot.pos, k);
    curTarget.current.lerp(shot.target, k);
    camera.lookAt(curTarget.current);
  });

  return null;
}
