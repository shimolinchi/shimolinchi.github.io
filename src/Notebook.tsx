import { useGLTF } from "@react-three/drei";
import { useEffect, useMemo } from "react";
import * as THREE from "three";

const MODEL_URL = "/models/notebook.glb";

export default function Notebook() {
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
      position={[-1.1, 1.37, -0.6]}
      rotation={[0, 0.3, 0]}
      scale={0.55}
    />
  );
}

useGLTF.preload(MODEL_URL);
