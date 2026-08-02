import { useEffect, useMemo } from "react";
import { useGLTF } from "@react-three/drei";
import * as THREE from "three";

const MODEL_URL = "/models/character.glb";

export default function Character() {
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

  return (
    <primitive
      object={model}
      position={[0, 0.07, -0.06]}
      rotation={[0, Math.PI, 0]}
      scale={2.4}
    />
  );
}

useGLTF.preload(MODEL_URL);
