import { OrbitControls } from "@react-three/drei";
import { useFrame, useThree } from "@react-three/fiber";
import { useEffect, useRef } from "react";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import * as THREE from "three";
import { useStore } from "./store";
import { SHOTS } from "./content";

export default function CameraRig() {
  const controls = useRef<OrbitControlsImpl>(null);
  const { camera } = useThree();
  const focus = useStore((state) => state.focus);

  useEffect(() => {
    const shot = SHOTS[focus];
    camera.position.copy(shot.pos);
    controls.current?.target.copy(shot.target);
    controls.current?.update();
  }, [camera, focus]);

  useFrame(() => {
    const orbit = controls.current;
    if (!orbit) return;

    const previousTarget = orbit.target.clone();
    orbit.target.x = THREE.MathUtils.clamp(orbit.target.x, -1.35, 3.1);
    orbit.target.y = THREE.MathUtils.clamp(orbit.target.y, 0.65, 2.45);
    orbit.target.z = THREE.MathUtils.clamp(orbit.target.z, -1.8, 0.35);

    if (!orbit.target.equals(previousTarget)) {
      camera.position.add(orbit.target.clone().sub(previousTarget));
      orbit.update();
    }
  });

  return (
    <OrbitControls
      ref={controls}
      makeDefault
      enableDamping
      dampingFactor={0.08}
      enablePan
      enableRotate
      enableZoom
      minDistance={0.75}
      maxDistance={9}
      minPolarAngle={0.12}
      maxPolarAngle={Math.PI / 2.02}
      zoomSpeed={1.1}
      rotateSpeed={0.75}
      panSpeed={0.8}
      screenSpacePanning
      mouseButtons={{
        LEFT: THREE.MOUSE.PAN,
        MIDDLE: THREE.MOUSE.ROTATE,
        RIGHT: THREE.MOUSE.PAN,
      }}
    />
  );
}
