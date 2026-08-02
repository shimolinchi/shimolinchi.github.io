import Character from "./Character";
import DeskEquipment from "./DeskEquipment";
import Desk from "./Desk";
import Hotspot from "./Hotspot";
import Notebook from "./Notebook";
import ToolCabinet from "./ToolCabinet";
import Trophy from "./Trophy";

export default function Scene() {
  return (
    <group>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0, 0]} receiveShadow>
        <circleGeometry args={[9, 48]} />
        <meshToonMaterial color="#9babb2" />
      </mesh>

      <Desk />

      <Hotspot id="person" bounce={0.05}>
        <Character />
      </Hotspot>

      <Hotspot id="computer">
        <DeskEquipment />
      </Hotspot>

      <Hotspot id="notebook" bounce={0.06}>
        <Notebook />
      </Hotspot>

      <Hotspot id="toolrack">
        <ToolCabinet />
      </Hotspot>

      <Hotspot id="trophy" bounce={0.03}>
        <Trophy />
      </Hotspot>
    </group>
  );
}
