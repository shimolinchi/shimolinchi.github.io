import { useGLTF } from "@react-three/drei";
import { useEffect, useMemo } from "react";
import * as THREE from "three";

const MODEL_URL = "/models/wooden-desk.glb";

export default function Desk() {
  const { scene } = useGLTF(MODEL_URL);
  const model = useMemo(() => scene.clone(true), [scene]);

  useEffect(() => {
    model.traverse((object) => {
      if (object instanceof THREE.Mesh) {
        object.castShadow = true;
        object.receiveShadow = true;
      }
    });
  }, [model]);

  return <primitive object={model} position={[0, 0, -1.1]} scale={3.35} />;
}

useGLTF.preload(MODEL_URL);
