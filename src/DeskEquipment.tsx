import { useGLTF } from "@react-three/drei";
import { useEffect, useMemo } from "react";
import * as THREE from "three";
import { useStore } from "./store";

function PropModel({ url, position, rotation = [0, 0, 0], scale, visible = true }: {
  url: string;
  position: [number, number, number];
  rotation?: [number, number, number];
  scale: number;
  visible?: boolean;
}) {
  const { scene } = useGLTF(url);
  const model = useMemo(() => scene.clone(true), [scene]);

  useEffect(() => {
    model.traverse((object) => {
      if (object instanceof THREE.Mesh) {
        object.castShadow = true;
        object.receiveShadow = true;
      }
    });
  }, [model]);

  return (
    <primitive
      object={model}
      position={position}
      rotation={rotation}
      scale={scale}
      visible={visible}
    />
  );
}

export function Monitor() {
  const hideMonitorForPersonShot = useStore(
    (state) => {
      if (state.viewMode === "free") return false;
      if (state.guidedTransitionStage === "person-to-computer-before") return true;
      if (state.guidedTransitionStage === "person-to-computer-after") return false;
      if (state.guidedTransitionStage === "computer-to-person-before") return false;
      if (state.guidedTransitionStage === "computer-to-person-after") return true;
      return state.focus === "person";
    },
  );

  return (
    <PropModel
      url="/models/monitor-v3.glb"
      position={[0, 1.36, -0.98]}
      scale={1.18}
      visible={!hideMonitorForPersonShot}
    />
  );
}

export function KeyboardAndMouse() {
  return (
    <group>
      <PropModel url="/models/keyboard.glb" position={[0.05, 1.35, -0.55]} scale={0.72} />
      <PropModel
        url="/models/mouse.glb"
        position={[0.62, 1.35, -0.45]}
        rotation={[0, -Math.PI / 2, 0]}
        scale={0.18}
      />
    </group>
  );
}

useGLTF.preload("/models/monitor-v3.glb");
useGLTF.preload("/models/keyboard.glb");
useGLTF.preload("/models/mouse.glb");
