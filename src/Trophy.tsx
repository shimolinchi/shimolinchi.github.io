import { useGLTF } from "@react-three/drei";
import { useEffect, useMemo } from "react";
import * as THREE from "three";

const MODEL_URL = "/models/trophy.glb";

export default function Trophy() {
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

  return <primitive object={model} position={[-1.35, 1.36, -1.62]} scale={0.52} />;
}

useGLTF.preload(MODEL_URL);
