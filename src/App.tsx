import { Canvas } from "@react-three/fiber";
import { Suspense } from "react";
import Scene from "./Scene";
import CameraRig from "./CameraRig";
import Overlay from "./Overlay";

export default function App() {
  return (
    <>
      <Canvas
        shadows
        dpr={[1, 2]}
        camera={{ position: [6, 5, 8], fov: 45 }}
        gl={{ antialias: true }}
      >
        {/* 搞怪暖色天空背景 + 雾 */}
        <color attach="background" args={["#ffcf87"]} />
        <fog attach="fog" args={["#ffcf87", 14, 30]} />

        <ambientLight intensity={0.75} />
        <directionalLight
          position={[5, 9, 4]}
          intensity={1.8}
          castShadow
          shadow-mapSize={[1024, 1024]}
        />
        <directionalLight position={[-6, 4, -3]} intensity={0.5} color="#8ab6ff" />

        <Suspense fallback={null}>
          <Scene />
        </Suspense>
        <CameraRig />
      </Canvas>
      <Overlay />
    </>
  );
}
