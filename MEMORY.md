# Project Memory

## Asset conventions

- Source GLBs live in `assets/` and use lowercase kebab-case English names. Do not overwrite source geometry; derived web assets go to `public/models/`.
- Current source assets:
  - `detailed-human-head.glb`, `seated-office-person.glb`
  - `computer-monitor.glb`, `monitor-white-legacy.glb`
  - `mechanical-keyboard-white.glb`, `wireless-mouse-white.glb`
  - `wooden-desk.glb`, `workbench-tool-cabinet.glb`
  - `notebook.glb`, `trophy.glb`
- Local Blender intermediates and renders in `output/`, `work/`, and `tmp/` are intentionally ignored by Git.

## Blender and web scene

- Head/body source models are non-manifold scans. Earlier automatic fusion attempts produced fragments, holes, overlaps, and UV seams. The clean manual restart is kept locally in `output/head_swap/head_body_restart.blend`; scripts use the renamed source files above.
- The manually joined character is exported to `public/models/character.glb` and rendered at `[0,0.07,-0.06]`, Y rotation `Math.PI`, scale `2.4`.
- Current desk scene placements:
  - desk `[0,0,-1.1]`, scale `3.35`
  - monitor v3 `[0,1.36,-0.98]`, scale `1.18`
  - keyboard `[0.05,1.35,-0.55]`, scale `0.72`
  - mouse `[0.62,1.35,-0.45]`, Y rotation `-Math.PI/2`, scale `0.18`
  - notebook `[-1.1,1.33,-0.6]`, X rotation `-0.035`, Y rotation `0.3`, scale `0.55`
  - tool cabinet `[2.95,0,-1.45]`, scale `1.8`
  - trophy `[-1.35,1.36,-1.62]`, scale `0.52`
- Camera uses SolidWorks-like middle-drag orbit controls. Distance is limited to `0.75–9`, and pan targets are clamped around the workstation.
- Camera has two modes managed in Zustand: default `guided` and interactive `free`. The initial page opens directly at the second preset (`person`), including matching camera position/target with no startup fly-in. Guided mode has six ordered presets (`overview`, `person`, `computer`, `notebook`, `trophy`, `toolrack`); wheel input switches presets with an eased camera/target transition and a 650 ms guard. Free mode restores OrbitControls. The top-center glass controls use a pin icon for fixed guided views and a bidirectional-arrow icon for free movement; buttons expand to labeled capsules on hover, and guided mode exposes six status dots.
- The first three guided shots were customized: overview starts from the opposite left side at `[-6,5,8]`; person uses a frontal camera at `[0.15,2.45,-2.65]`; computer places the camera safely between the person and monitor at `[0,1.95,-0.28]` so the character is outside the screen-focused frame without camera/character intersection.
- Guided-shot occlusion rules: the monitor is temporarily hidden for the frontal person preset; the character is temporarily hidden for the computer preset, allowing that camera to sit farther back at `[0,2.12,0.82]`. Both models return in other presets and free mode. Hotspot hover scaling/bouncing is disabled in guided mode while click interaction remains available.
- Only the person/computer pair has a custom transition; other presets retain exponential response `4.2`. Both directions share the same reversible `1.55s` centripetal Catmull-Rom arc, passing moderately around the left side near `[-2.25,2.82,1.35]` without a midpoint stop. At 48% progress, symmetric before/after stages swap character and monitor visibility, fixing reverse transitions.
- The shared person/computer arc now uses `getPointAt` arc-length sampling with linear progress for constant physical camera speed. Character and monitor remain mounted and switch Three.js `visible` flags instead of React unmount/remount, preventing the mid-transition frame hitch.
- Guided detail presets (`guidedIndex > 0`) animate the perspective camera `filmOffset` toward `7.2`, moving the 3D subject left without changing world-space camera paths; overview and free mode return to zero offset. The desktop info panel is a full-height right rail (`clamp(390px,36vw,520px)`) flush to the top, bottom, and right, with enlarged typography and left-side rounding. Mobile retains a bottom card layout.
- Tool cabinet moved from the desk's right to its left at `[-2.95,0,-1.45]`; its preset and free-camera X clamp were mirrored accordingly. The full-height info rail has two 46px glass controls: the top-left arrow expands to full-screen, while the top-right arrow collapses the rail to a 60px right-edge strip. The remaining arrow restores the normal rail.
- Free mode hotspot clicks only select and open the object's information panel; they do not move the camera or apply guided-mode character/monitor occlusion. OrbitControls remain continuously available.
- The computer hotspot is split: only the monitor gets the free-mode hover scale/bounce animation; keyboard and mouse remain stationary while retaining the same clickable computer information behavior.
- The right information rail uses a structured header, category kicker, numbered information cards, and a footer action. Its content has independent overflow scrolling; copy remains centralized in `src/content.tsx`, layout in `src/Overlay.tsx`, and presentation in `src/index.css`.
- Every hotspot click increments `panelRequestId`; `Overlay` uses it to reopen the normal rail even when the same object is clicked again after the panel was collapsed or fullscreen. This fixes the free-mode stale panel state.
- Portfolio content categories are now: notebook = papers and patents, trophy = chronological awards, tool cabinet = mechanical/structure projects, monitor = algorithm projects. Each record is a structured `PanelItem` with date, title, optional description, and external link. The small category kicker was removed; the emoji now sits directly before the main title.
- The information rail no longer includes the bottom “返回全景” button or exploration hint; navigation remains through guided dots, mode controls, and the rail controls.
- Guided-mode wheel navigation ignores wheel events originating inside `.info-panel`, so hovering the right rail scrolls its list instead of changing camera presets.
- The person panel includes public resume-based education, research focus, 2025 robotics teleoperation internship, technical stack, and research/competition highlights. Private contact details remain excluded.
- Scene background/fog is cool gray-blue `#c8d6dd`, with ground `#9babb2` and neutral hemisphere lighting.
- Trophy, character, computer, notebook, and tool cabinet are clickable hotspots. Portfolio text includes only public resume highlights; private contact details are excluded.
- Always run `npm.cmd run build` after scene or asset changes.
