import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

// 搞怪占位小人：大脑袋 + 呆毛 + 会转的眼珠，坐在椅子上
export default function Character() {
  const head = useRef<THREE.Group>(null);
  const leye = useRef<THREE.Mesh>(null);
  const reye = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    const t = state.clock.elapsedTime;
    if (head.current) {
      head.current.rotation.z = Math.sin(t * 1.3) * 0.06; // 脑袋左右晃
      head.current.rotation.y = Math.sin(t * 0.7) * 0.15;
    }
    // 眼珠乱瞟
    const gx = Math.sin(t * 2.1) * 0.03;
    const gy = Math.cos(t * 1.7) * 0.02;
    [leye, reye].forEach((e) => e.current && e.current.position.set(e.current.position.x, 2.32 + gy, 0.31 + gx));
  });

  return (
    <group position={[0, 0, -0.2]}>
      {/* 身体 */}
      <mesh position={[0, 1.5, 0]} castShadow>
        <capsuleGeometry args={[0.35, 0.6, 8, 16]} />
        <meshToonMaterial color="#ff6f61" />
      </mesh>
      {/* 大脑袋 */}
      <group ref={head} position={[0, 2.15, 0]}>
        <mesh castShadow>
          <sphereGeometry args={[0.42, 32, 32]} />
          <meshToonMaterial color="#ffe0bd" />
        </mesh>
        {/* 呆毛 */}
        <mesh position={[0, 0.45, 0]} rotation={[0, 0, 0.3]}>
          <coneGeometry args={[0.05, 0.35, 8]} />
          <meshToonMaterial color="#3a2a1a" />
        </mesh>
        {/* 头发块 */}
        <mesh position={[0, 0.18, -0.05]}>
          <sphereGeometry args={[0.44, 24, 24, 0, Math.PI * 2, 0, Math.PI / 2.2]} />
          <meshToonMaterial color="#3a2a1a" />
        </mesh>
        {/* 眼睛白 */}
        <mesh position={[-0.15, 2.32 - 2.15, 0.3]}>
          <sphereGeometry args={[0.1, 16, 16]} />
          <meshBasicMaterial color="white" />
        </mesh>
        <mesh position={[0.15, 2.32 - 2.15, 0.3]}>
          <sphereGeometry args={[0.1, 16, 16]} />
          <meshBasicMaterial color="white" />
        </mesh>
      </group>
      {/* 眼珠（世界坐标随 head 外，简单跟随） */}
      <mesh ref={leye} position={[-0.15, 2.32, 0.31]}>
        <sphereGeometry args={[0.05, 12, 12]} />
        <meshBasicMaterial color="#111" />
      </mesh>
      <mesh ref={reye} position={[0.15, 2.32, 0.31]}>
        <sphereGeometry args={[0.05, 12, 12]} />
        <meshBasicMaterial color="#111" />
      </mesh>

      {/* 办公椅：座垫 + 靠背 + 中柱 */}
      <mesh position={[0, 0.95, 0]} castShadow>
        <boxGeometry args={[0.85, 0.15, 0.8]} />
        <meshToonMaterial color="#333844" />
      </mesh>
      <mesh position={[0, 1.4, -0.4]} castShadow>
        <boxGeometry args={[0.85, 0.9, 0.14]} />
        <meshToonMaterial color="#333844" />
      </mesh>
      <mesh position={[0, 0.55, 0]}>
        <cylinderGeometry args={[0.07, 0.07, 0.8, 12]} />
        <meshToonMaterial color="#222" />
      </mesh>
    </group>
  );
}
