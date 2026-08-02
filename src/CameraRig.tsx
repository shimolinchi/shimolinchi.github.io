import { OrbitControls } from "@react-three/drei";
import { useFrame, useThree } from "@react-three/fiber";
import { useEffect, useRef } from "react";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import * as THREE from "three";
import { SHOTS } from "./content";
import { GUIDED_FOCUSES, useStore } from "./store";

const CAMERA_EASING = 4.2;
const PERSON_COMPUTER_DURATION = 1.55;
const MODEL_SWAP_PROGRESS = 0.48;
const WHEEL_COOLDOWN = 650;

const PERSON_POSITION = SHOTS.person.pos.clone();
const COMPUTER_POSITION = SHOTS.computer.pos.clone();
const PERSON_TARGET = SHOTS.person.target.clone();
const COMPUTER_TARGET = SHOTS.computer.target.clone();

const POSITION_PATH = new THREE.CatmullRomCurve3(
  [
    PERSON_POSITION,
    new THREE.Vector3(-1.85, 2.82, -2.45),
    new THREE.Vector3(-2.25, 2.82, 1.35),
    new THREE.Vector3(-1.1, 2.42, 1.8),
    COMPUTER_POSITION,
  ],
  false,
  "centripetal",
);

const TARGET_PATH = new THREE.CatmullRomCurve3(
  [
    PERSON_TARGET,
    new THREE.Vector3(-0.45, 1.88, -0.55),
    new THREE.Vector3(-0.3, 1.78, -0.9),
    COMPUTER_TARGET,
  ],
  false,
  "centripetal",
);

export default function CameraRig() {
  const controls = useRef<OrbitControlsImpl>(null);
  const { camera } = useThree();
  const viewMode = useStore((state) => state.viewMode);
  const guidedIndex = useStore((state) => state.guidedIndex);
  const setGuidedIndex = useStore((state) => state.setGuidedIndex);
  const setTransitionStage = useStore((state) => state.setGuidedTransitionStage);

  const targetPosition = useRef(SHOTS.person.pos.clone());
  const targetLookAt = useRef(SHOTS.person.target.clone());
  const currentLookAt = useRef(SHOTS.person.target.clone());
  const previousGuidedIndex = useRef(1);
  const transitionElapsed = useRef(0);
  const pathDirection = useRef<1 | -1 | 0>(0);
  const modelsSwapped = useRef(false);
  const lastWheelAt = useRef(0);
  const currentFilmOffset = useRef(0);

  useEffect(() => {
    if (viewMode !== "guided") return;

    const shot = SHOTS[GUIDED_FOCUSES[guidedIndex]];
    targetPosition.current.copy(shot.pos);
    targetLookAt.current.copy(shot.target);

    const from = previousGuidedIndex.current;
    previousGuidedIndex.current = guidedIndex;
    pathDirection.current = from === 1 && guidedIndex === 2 ? 1 : from === 2 && guidedIndex === 1 ? -1 : 0;

    if (pathDirection.current !== 0) {
      transitionElapsed.current = 0;
      modelsSwapped.current = false;
      setTransitionStage(
        pathDirection.current === 1
          ? "person-to-computer-before"
          : "computer-to-person-before",
      );
    } else {
      setTransitionStage("idle");
    }
  }, [guidedIndex, setTransitionStage, viewMode]);

  useEffect(() => {
    if (viewMode === "free" && controls.current) {
      pathDirection.current = 0;
      setTransitionStage("idle");
      controls.current.target.copy(currentLookAt.current);
      controls.current.update();
    }
  }, [setTransitionStage, viewMode]);

  useEffect(() => {
    const onWheel = (event: WheelEvent) => {
      if (useStore.getState().viewMode !== "guided") return;
      if (event.target instanceof Element && event.target.closest(".info-panel")) return;
      event.preventDefault();
      if (Math.abs(event.deltaY) < 8 || pathDirection.current !== 0) return;

      const now = performance.now();
      if (now - lastWheelAt.current < WHEEL_COOLDOWN) return;
      lastWheelAt.current = now;

      const current = useStore.getState().guidedIndex;
      setGuidedIndex(current + (event.deltaY > 0 ? 1 : -1));
    };

    window.addEventListener("wheel", onWheel, { passive: false });
    return () => window.removeEventListener("wheel", onWheel);
  }, [setGuidedIndex]);

  useFrame((_, delta) => {
    const orbit = controls.current;
    const perspectiveCamera = camera as THREE.PerspectiveCamera;
    const desiredFilmOffset = viewMode === "guided" && guidedIndex > 0 ? 7.2 : 0;
    const framingAlpha = 1 - Math.exp(-5 * delta);
    currentFilmOffset.current = THREE.MathUtils.lerp(
      currentFilmOffset.current,
      desiredFilmOffset,
      framingAlpha,
    );
    perspectiveCamera.filmOffset = currentFilmOffset.current;
    perspectiveCamera.updateProjectionMatrix();

    if (viewMode === "guided") {
      if (pathDirection.current !== 0) {
        transitionElapsed.current += delta;
        const progress = Math.min(transitionElapsed.current / PERSON_COMPUTER_DURATION, 1);
        const pathProgress = pathDirection.current === 1 ? progress : 1 - progress;

        POSITION_PATH.getPointAt(pathProgress, camera.position);
        TARGET_PATH.getPointAt(pathProgress, currentLookAt.current);

        if (progress >= MODEL_SWAP_PROGRESS && !modelsSwapped.current) {
          modelsSwapped.current = true;
          setTransitionStage(
            pathDirection.current === 1
              ? "person-to-computer-after"
              : "computer-to-person-after",
          );
        }

        if (progress >= 1) {
          pathDirection.current = 0;
          setTransitionStage("idle");
        }
      } else {
        const alpha = 1 - Math.exp(-CAMERA_EASING * delta);
        camera.position.lerp(targetPosition.current, alpha);
        currentLookAt.current.lerp(targetLookAt.current, alpha);
      }

      camera.lookAt(currentLookAt.current);
      return;
    }

    if (!orbit) return;

    const previousTarget = orbit.target.clone();
    orbit.target.x = THREE.MathUtils.clamp(orbit.target.x, -3.1, 1.35);
    orbit.target.y = THREE.MathUtils.clamp(orbit.target.y, 0.65, 2.45);
    orbit.target.z = THREE.MathUtils.clamp(orbit.target.z, -1.8, 0.35);

    if (!orbit.target.equals(previousTarget)) {
      camera.position.add(orbit.target.clone().sub(previousTarget));
      orbit.update();
    }
    currentLookAt.current.copy(orbit.target);
  });

  return (
    <OrbitControls
      ref={controls}
      makeDefault
      enabled={viewMode === "free"}
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
