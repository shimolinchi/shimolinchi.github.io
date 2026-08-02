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
  - keyboard `[0.05,1.37,-0.55]`, scale `0.72`
  - mouse `[0.62,1.37,-0.45]`, Y rotation `-Math.PI/2`, scale `0.18`
  - notebook `[-1.1,1.37,-0.6]`, scale `0.55`
  - tool cabinet `[2.95,0,-1.45]`, scale `1.8`
  - trophy `[-1.35,1.36,-1.62]`, scale `0.52`
- Camera uses SolidWorks-like middle-drag orbit controls. Distance is limited to `0.75–9`, and pan targets are clamped around the workstation.
- Scene background/fog is cool gray-blue `#c8d6dd`, with ground `#9babb2` and neutral hemisphere lighting.
- Trophy, character, computer, notebook, and tool cabinet are clickable hotspots. Portfolio text includes only public resume highlights; private contact details are excluded.
- Always run `npm.cmd run build` after scene or asset changes.
