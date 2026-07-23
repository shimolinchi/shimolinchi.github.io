import Hotspot from "./Hotspot";
import Character from "./Character";

// 整个工位场景：地面 + 桌子 + 四个可点击热点（人/电脑/本子/工具架）
export default function Scene() {
  return (
    <group>
      {/* 地面圆盘 */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0, 0]} receiveShadow>
        <circleGeometry args={[9, 48]} />
        <meshToonMaterial color="#f7b26a" />
      </mesh>

      {/* 桌子：桌面 + 四条腿 */}
      <group position={[0, 0, -1.1]}>
        <mesh position={[0, 1.3, 0]} castShadow receiveShadow>
          <boxGeometry args={[4, 0.12, 1.4]} />
          <meshToonMaterial color="#c98a5e" />
        </mesh>
        {[[-1.9, -0.6], [1.9, -0.6], [-1.9, 0.6], [1.9, 0.6]].map(([x, z], i) => (
          <mesh key={i} position={[x, 0.65, z]} castShadow>
            <boxGeometry args={[0.12, 1.3, 0.12]} />
            <meshToonMaterial color="#8f5f3d" />
          </mesh>
        ))}
      </group>

      {/* 人物（热点：person） */}
      <Hotspot id="person" bounce={0.05}>
        <Character />
      </Hotspot>

      {/* 电脑（热点：computer）—— 显示器 + 会闪的屏幕 + 键鼠 */}
      <Hotspot id="computer">
        <group position={[0, 1.36, -1.1]}>
          <mesh position={[0, 0.45, 0]} castShadow>
            <boxGeometry args={[1.1, 0.65, 0.06]} />
            <meshToonMaterial color="#222831" />
          </mesh>
          <mesh position={[0, 0.45, 0.035]}>
            <planeGeometry args={[1, 0.55]} />
            <meshBasicMaterial color="#48c9ff" />
          </mesh>
          <mesh position={[0, 0.08, 0.15]}>
            <boxGeometry args={[0.5, 0.04, 0.2]} />
            <meshToonMaterial color="#111" />
          </mesh>
          {/* 键盘 + 鼠标 */}
          <mesh position={[-0.15, 0.04, 0.5]} castShadow>
            <boxGeometry args={[0.7, 0.05, 0.25]} />
            <meshToonMaterial color="#e8e8e8" />
          </mesh>
          <mesh position={[0.5, 0.04, 0.5]} castShadow>
            <capsuleGeometry args={[0.06, 0.08, 6, 12]} />
            <meshToonMaterial color="#e8e8e8" />
          </mesh>
        </group>
      </Hotspot>

      {/* 本子（热点：notebook） */}
      <Hotspot id="notebook" bounce={0.06}>
        <group position={[-1.1, 1.4, -0.6]} rotation={[0, 0.3, 0]}>
          <mesh castShadow>
            <boxGeometry args={[0.5, 0.06, 0.65]} />
            <meshToonMaterial color="#ff477e" />
          </mesh>
          <mesh position={[0, 0.035, 0]}>
            <boxGeometry args={[0.44, 0.02, 0.58]} />
            <meshToonMaterial color="#fff" />
          </mesh>
        </group>
      </Hotspot>

      {/* 工具架（热点：toolrack） */}
      <Hotspot id="toolrack">
        <group position={[2.6, 0, -1.4]}>
          {[0.6, 1.2, 1.8].map((y, i) => (
            <mesh key={i} position={[0, y, 0]} castShadow>
              <boxGeometry args={[1.1, 0.06, 0.5]} />
              <meshToonMaterial color="#6b4f3a" />
            </mesh>
          ))}
          {[[-0.5, -0.2], [0.5, -0.2], [-0.5, 0.2], [0.5, 0.2]].map(([x, z], i) => (
            <mesh key={"p" + i} position={[x, 1.1, z]}>
              <boxGeometry args={[0.06, 2, 0.06]} />
              <meshToonMaterial color="#4a3524" />
            </mesh>
          ))}
          {/* 架上小工具 */}
          <mesh position={[-0.3, 0.72, 0]} castShadow>
            <boxGeometry args={[0.2, 0.2, 0.2]} />
            <meshToonMaterial color="#ffd23f" />
          </mesh>
          <mesh position={[0.25, 1.32, 0]} castShadow>
            <cylinderGeometry args={[0.08, 0.08, 0.3, 12]} />
            <meshToonMaterial color="#3ddc84" />
          </mesh>
          <mesh position={[0, 1.92, 0]} castShadow>
            <sphereGeometry args={[0.14, 16, 16]} />
            <meshToonMaterial color="#48c9ff" />
          </mesh>
        </group>
      </Hotspot>
    </group>
  );
}
