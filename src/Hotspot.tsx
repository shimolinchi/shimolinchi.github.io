import { useRef, useState, type ReactNode } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { useStore, type Focus } from "./store";

// 把一组物体包成「可点击热点」：悬停放大 + 轻微弹跳，点击切换焦点
export default function Hotspot({
  id,
  children,
  bounce = 0.04,
}: {
  id: Focus;
  children: ReactNode;
  bounce?: number;
}) {
  const ref = useRef<THREE.Group>(null);
  const [hover, setHover] = useState(false);
  const setFocus = useStore((s) => s.setFocus);
  const setHovered = useStore((s) => s.setHovered);
  const base = useRef(0);

  useFrame((state) => {
    if (!ref.current) return;
    const t = state.clock.elapsedTime;
    const target = hover ? 1.08 : 1;
    const s = ref.current.scale.x + (target - ref.current.scale.x) * 0.15;
    ref.current.scale.setScalar(s);
    // 悬停时上下弹跳，搞怪感
    ref.current.position.y = base.current + (hover ? Math.sin(t * 6) * bounce : 0);
  });

  return (
    <group
      ref={ref}
      onPointerOver={(e) => {
        e.stopPropagation();
        setHover(true);
        setHovered(id);
        document.body.style.cursor = "pointer";
      }}
      onPointerOut={() => {
        setHover(false);
        setHovered(null);
        document.body.style.cursor = "auto";
      }}
      onClick={(e) => {
        e.stopPropagation();
        setFocus(id);
      }}
    >
      {children}
    </group>
  );
}
