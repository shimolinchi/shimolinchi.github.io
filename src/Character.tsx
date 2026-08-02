import { useEffect, useMemo } from "react";
import { useGLTF } from "@react-three/drei";
import * as THREE from "three";
import { useStore } from "./store";

const MODEL_URL = "/models/character.glb";

export default function Character() {
  const hideForComputerShot = useStore(
    (state) => {
      if (state.viewMode === "free") return false;
      if (state.guidedTransitionStage === "person-to-computer-before") return false;
      if (state.guidedTransitionStage === "person-to-computer-after") return true;
      if (state.guidedTransitionStage === "computer-to-person-before") return true;
      if (state.guidedTransitionStage === "computer-to-person-after") return false;
      return state.focus === "computer";
    },
  );
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
      visible={!hideForComputerShot}
      position={[0, 0.07, -0.06]}
      rotation={[0, Math.PI, 0]}
      scale={2.4}
    />
  );
}

useGLTF.preload(MODEL_URL);
