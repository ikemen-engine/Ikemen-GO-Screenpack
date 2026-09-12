# work

Editable source files for the packed assets in this repository. Nothing here is loaded by the engine — it is only needed to re-render or re-pack an asset.

## Formats

| Format | Notes |
|---|---|
| `.png` | Exported sprites, named `group-image` (e.g. `100-0.png`). |
| `.act` | MUGEN/Ikemen palettes. |
| `.wav` | Sound samples, named `group-sample` (e.g. `900-3.wav`). |
| `.clip` | Clip Studio Paint documents (the layered artwork). Provided as is; you may resave them as PSD if you prefer another editor. |
| `.psd` | `glyphs/template_btns.psd` — template for drawing new button glyphs. |
| `.blend` | `ik_logo/` — Blender scene used to render `video/ik_logo.webm`. |
| `.ase` / `.pcx` / `-sff.def` | `font/Menu2` only: Aseprite source, exported sheet, and a Fighter Factory sprite-cutting script for it. |

## Re-packing

Each folder with sprites or sounds contains an `import.ffe` script. Open Fighter Factory 3 (or later), create/open the target file and execute the script on the `import.ffe` — it adds every sprite (with axes and palette) or sound in the folder in the right order.

## Folder → packed file

| Folder | Packed file |
|---|---|
| `system/` | `data/ikemen1/system.sff`, `data/system.snd` |
| `fight/` | `data/fight.sff`, `data/fight.snd` |
| `fightfx/` | `data/fightfx.sff` |
| `common/sound/` | `data/common.snd` |
| `gofx/` | `data/gofx/gofx.sff`, `data/gofx/gofx.snd` |
| `glyphs/` | `data/glyphs.sff` |
| `font/<Name>/` | `data/ikemen1/fonts/<Name>.sff` |
| `font/default*` | engine-side `font/default-3x5*.sff` |
| `ik_logo/` | `video/ik_logo.webm` |
