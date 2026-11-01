# Atlas handoff — 2026-11-01

## Start here

The current addon is **Atlas 0.7.0**, an Ashita v4 / LuaJIT FFXI map browser.
The latest feature is a first boat/airship POI layer. Implementation and offline
checks are complete for that slice; user feedback and live game validation remain
the next useful work. Do not interpret earlier chat plans as unfinished assignments.

- Game/workspace: `D:\Games\HorizonXI\HorizonXI\Game`
- Addon: `D:\Games\HorizonXI\HorizonXI\Game\addons\atlas`
- Shell: PowerShell. Run the Python commands below from the Game directory.
- Reload in game: `/addon reload atlas`. Open/toggle: `/atlas`.
- [README.md](README.md) describes current controls, source pipelines and credits.
- The Game root is not a Git repository. No commit, PR or deployment was created
  as part of this work. Changes and built runtime assets are already in place.

## User intent and decisions to preserve

The primary goal is **making zone interconnections obvious**, including clicking
an exit and opening the destination map at its corresponding entrance.

1. The original world → region → zone proposal has been superseded. Runtime is
   now **world ↔ zone** on one continuous, zoomable world canvas.
2. **Region names are not clickable.** Their hover highlighting was also removed.
   Zone banners remain clickable at closer world zoom (`zoom >= 2.5`).
3. Outward scrolling from a zone's minimum zoom, right-clicking a zone, and the
   World button open the world around the **current/destination zone**, including
   after following an exit. Do not send the user back to an unrelated overview.
   Back/Forward preserve prior camera and arrival state.
4. Open `/atlas` / `/atlas show` to the player's current zone/floor by default,
   centered on them. Defer location during zoning rather than choosing a stale
   floor. Unsupported zones fall back to the world map.
5. Keep UI text sparse: no explainer sidebar. Existing map exit graphics are the
   controls, with invisible larger catchments and a small hover outline. Do not
   reintroduce opaque exit buttons or cover Remapster exit numbers.
6. The user requested a manual hit-area editor. Its saved rectangles override
   imported/default areas; preserve these when regenerating map data.
7. Prefer deterministic cached wiki/server/native-map matching for expansion.
   Earlier parallel model/Antigravity experiments are historical, not the current
   production tagging method. Do not automatically launch another model run.
8. The user reported inconsistent party locations and world zoom lag. Fixes have
   offline coverage, but their live behavior has not been confirmed by the user.

Area-name commands such as `/atlas ronfaure` still exist as **world camera
shortcuts**. `N.go(..., 'region', ...)` is an internal compatibility alias that
creates a world view; it is not a remaining region screen.

## Current coverage

| Item | Current state |
| --- | --- |
| Native zone/floor maps | 236 |
| Walking passage records | 394, including existing one-way restrictions |
| Original catalog | 40 maps / 56 passages: 31 legacy seed + 25 artwork-reviewed (`117` baseline polygon click areas) |
| Deterministic extension | 196 maps / 338 reciprocal passage pairs (`596` expanded polygon click areas) |
| Region groupings | All 18 regions: Ronfaure, Zulkheim, Norvallen, Fauregandi, Gustaberg, Derfland, Valdeaunia, Vollbow, Qufim, Aragoneu, Kolshushu, Sarutabaruta, Li'Telor, Tu'Lia, Kuzotz, Elshimo Lowlands, Elshimo Uplands, Tavnazian Archipelago; cities grouped with neighboring areas |
| Full world artwork | 8192 × 8192 native connected artwork, zoom/pan over the full world |
| Interactive zone coverage | Supported catalog only (`236` maps across `18` regions); `16` multi-floor native variants and `148` directed source connections remain held where artwork/pulse matching is ambiguous |
| Transport POIs | 5 routes, 7 world hubs, 10 route endpoints, 9 native boarding markers |

The extension also adds connections between previously supported regions and newly
added regions across the continent.

### Latest: boats and airships

- Ferry: Selbina ↔ Mhaura.
- Airships: Jeuno ↔ San d'Oria, Bastok, Windurst and Kazham.
- Jeuno's four services share a world icon; its zone map has four dock icons.
- Hover world icons for destinations and route lines. Click a supported hub to
  open its port map. Click a zone dock icon for destination choices.
- Selecting a mapped destination centers on its dock (including Port Windurst and
  Kazham). **Mhaura's ferry endpoint remains world-only** because the wiki's Mhaura
  map (`14.json`) omits a connection pulse for Selbina (`161`); selecting Mhaura from
  Selbina centers/highlights Mhaura's world marker, while clicking Mhaura's world hub
  opens the Mhaura zone map.
- Independent Boats / Airships filters are under `... → Points of interest`.
- Ticket/pass requirements are informational. There are no live schedules, fares,
  pass-ownership checks, travel automation or character movement.
- Barges, Manaclipper and other ferry services have not been added to this first set.
- Transport is separate from the walking passage graph. Do not import airships as
  ordinary walking exits while expanding map connections.

## Where changes belong

All paths in this table are relative to the addon directory.

| File | Responsibility |
| --- | --- |
| `atlas.lua` | Version, event registration, commands and zone packet state |
| `src/ui.lua` | World/zone canvas, toolbar, hit handling, actor markers, transport icons/popups |
| `src/navigation.lua` | View/history, exit arrival focus, world return camera, zoom math |
| `src/world.lua` | Zone neighborhood bounds, visible world pages, progressive loading/cache policy |
| `src/client.lua` | Native map table/floor lookup, CRT/XIPivot DAT reading, D3D textures, live player/group positions |
| `src/dat_image.lua` | DAT image validation and bitmap/DXT wrapping |
| `src/catalog.lua` | Merges reviewed baseline + deterministic extension, exits, floor/city tabs |
| `src/hotspots.lua` | Default rectangles + imported polygons + manual override precedence and persistence |
| `src/exit_editor.lua` | Draw/move/resize, Undo/Reset, editor state |
| `src/pois.lua` | Category filters, transport grouping/indexing, links and destination browsing |
| `data/catalog.lua`, `data/regions.lua` | Original generated reviewed baseline; preserve its provenance |
| `data/expansion.lua`, `data/expanded_hotspots.lua` | Generated extension and its polygon areas |
| `data/wiki_hotspots.lua` | Generated original wiki-import click areas |
| `data/world_art.lua`, `assets/world/` | Generated world metadata and 85 texture pages |
| `data/pois.lua` | Generated transport categories, hubs, stops and routes |

`src/region.lua`, `src/regions.lua`, `data/regional_art.lua`,
`data/expanded_regions.lua`, and `assets/regions/` remain **authoring/build
dependencies**, not a runtime region UI. The world builder derives zone banners
and bounds from them. Removing them because the screen was retired will break
the current build pipeline.

Runtime does not require Boussole to be loaded and imports no Boussole modules.
The authoring expansion reads the local Boussole zone/floor lists as candidates,
then checks actual installed native map-table entries and DAT identities.
Do not change Boussole or other addons to make Atlas work.

### Coordinates and saved user data

- Zone geometry always uses top-left-origin **512 × 512 reference pixels**,
  regardless of original/HD texture dimensions.
- World geometry uses top-left-origin **8192 × 8192 native pixels**.
- Exit mouths (`x/y`), printed badge anchors, and arrival focus can be different.
  Do not substitute a printed label location for a physical entrance or arrival.
- Game positions use native signed scale/offset transforms. In source zone-line
  arrays, the middle coordinate is vertical height; project horizontal X/Z.
- Manual rectangles save to
  `D:\Games\HorizonXI\HorizonXI\Game\config\addons\atlas\exit-areas.json`,
  with a previous valid `.json.bak`. Do not overwrite/delete them during builds.
- Reset removes the manual rectangle and restores imported/default hit behavior.
- Current display/category toggles are in-memory, not persisted preferences.

## World artwork and performance

The closer interconnected-zone artwork is **native wiki zoom level 5**. Earlier
requests explored levels 2/3; do not revert to those semantic artwork layers.

- Master: `exports/horizon-connected-z5/connected-world.png` (8192²), built from
  1024 original 256² source JPEGs, without screenshot stitching/resampling.
- Manifest, tile/pixel verification and offline viewer live beside it;
  `view-map.html` works locally.
- Runtime: `assets/world/connected-lod{2..5}-X-Y.png` with 1 + 4 + 16 + 64 pages.
  Each page is 1024². Lower levels downsample the **same level-5 artwork** so
  switching detail levels never changes map geometry.
- Only visible detail is requested. A coarse complete map stays underneath
  cached detail so missing pages do not make holes.
- Scrolling/panning defers fine loads until 120 ms after the gesture; at most one
  new page loads per frame, nearest the view center first.
- `client.keep_assets(...,24)` retains a bounded recent-use cache across zoom
  changes and while viewing zones. Intermediate fallback levels are trimmed so
  cached overlays do not exceed the page budget on large windows.
- The PNG asset loader uses `D3DXCreateTextureFromFileInMemoryEx` with **one mip
  level**; the pyramid already supplies levels. Re-enabling automatic mip-chain
  generation or loading all visible PNGs synchronously can reintroduce zoom lag.
- Texture owners must be released on eviction/clear/unload. DAT map cache entries
  are separate from world asset entries.
- Coarse artwork failure falls back to the original Conquest DAT. `... → Reload
  maps` clears caches and allows retry. The fallback has no region click targets.
- POI glyphs are vector draw calls and do not load additional textures.

The runtime asset and streaming tests passed. Actual Direct3D upload latency,
frame rate and perceived smoothness still need an in-game check; no FPS benchmark
was taken. On a cold view, detail intentionally sharpens after scrolling stops.

## Sources and deterministic authoring

### Walking maps and entrances

- Main tool: `tools/expand_regions.py fetch|build`.
- Inputs/reports: `annotations/expansion/`: `sources.json`, `server-paths.json`,
  `floor-matches.json`, `draft-maps.json`, `connection-review.json`, `build.json`,
  `REPORT.md`, and manually measured `world-anchors.json`.
- `CORE` declares all 14 expansion regions (`gustaberg`, `derfland`, `valdeaunia`,
  `vollbow`, `qufim`, `aragoneu`, `kolshushu`, `sarutabaruta`, `litelor`, `tulia`,
  `kuzotz`, `elshimo_lowlands`, `elshimo_uplands`, `tavnazian_archipelago`).
- Floor candidates come from local lists and are verified against installed
  `FFXiMain.dll` / DAT identities (`ROM\283\70.DAT` for `Hall of the Gods`,
  `zone=251, floor=1`, carries internal header `m_251_00` and is explicitly
  validated). Later high-index variants (`index >= 300`) are intentionally outside
  this era pilot, not automatically accepted.
- Multi-floor artwork matching removes common grid/parchment pixels, then uses
  mutual-best discriminating ink matches (score ≥ .20; both margins ≥ .035).
- Native-floor resolution uses nearby wiki entrances; reciprocal endpoint pairing
  requires each side within 24 reference pixels and a useful runner-up margin.
  See the code for the complete thresholds; do not lower them just to raise counts.
- Unique reciprocal wiki links provide stairs/fallbacks when source coordinates
  do not match. Unpaired server candidates must not suppress valid wiki fallbacks.
  Lower Jeuno ↔ Port Jeuno was a concrete regression case here.
- Cross-source nearby duplicates are removed. Reverse directions of curated
  one-way drops and remote-city transport links are protected/excluded.
- Public LandSandBoat source correlation is **not verified Horizon traversal**.
  New records are `source_correlated`; reviewed baseline records retain their own
  statuses. Do not relabel them as traversal-verified without actual evidence.

The older `tools/import_horizon.py fetch|build` imports supplementary polygon
click areas using an explicit pilot crosswalk, parses candidate server positions,
and calls `tools/build_regional_art.py` to rebuild authoring boards. Its
`runtime_connectivity_changed: false` refers to the **original catalog only**;
the extension is reported separately.

Pinned sources currently include:

- Wiki module: `annotations/imports/horizon/ffximap.js`; extract embedded JSON
  without executing downloaded JavaScript.
- Wiki module SHA256:
  `0f8d0ec7e08544a09915225f8bd62d42d6fbf622c6ff78ddbbbec60a67f3db86`.
- LandSandBoat commit: `1450874235d41341a2ced74c1dbbe9e4477611d2`.
- Baseline catalog SHA256:
  `ca49f7c43c2482bc5ea0260920bae0416f03df638c0a83295de5ffbe71d8c103`.
- Baseline manifest SHA256:
  `aeec276f8e91293c6c636be52712854c687f0b8ee6db2f1893af0b111b3bfc43`.

Original review contracts and the prior model experiment live in
`annotations/CONTRACT.md`, `PILOT_REPORT.md`, and
`annotations/experiments/flash38/REPORT.md`. Read those if changing the reviewed
baseline. Do not casually rerun annotation preparation/reviews or `agy` jobs;
they are not prerequisites for source-driven expansion.

### POIs

Edit `annotations/poi/transport.json`; run `tools/build_pois.py` to regenerate
`data/pois.lua` and `annotations/poi/build.json`. Supported dock coordinates are
wiki game-world boarding pulses projected through the installed native map
transform, not guesses from grid labels. World-only town markers are explicit
measured anchors. Unmapped destinations remain world-only instead of inventing
a native floor. Category/location/link data is separate from the walking graph.

### Build order when source/layout changes warrant regeneration

```powershell
python addons/atlas/tools/expand_regions.py build
python addons/atlas/tools/import_horizon.py build
python addons/atlas/tools/build_world_art.py
python addons/atlas/tools/build_pois.py
```

These use cached inputs and work offline. For missing caches, the relevant
`expand_regions.py fetch` / `import_horizon.py fetch` commands fetch public data
and retain fingerprints. To recreate the full master if missing:

```powershell
python addons/atlas/tools/export_world_art.py --zoom 5
```

The full exporter needs all source tiles; do not fetch/rebuild everything merely
to change UI code. Inspect exit codes before continuing dependent builds.

`exports/`, raw tile caches, copied wiki floor images, annotation packets/sheets
and exploratory previews are ignored local authoring artifacts. They are present
in this workspace but may be absent in a fresh copy. Built `data/*.lua` and runtime
`assets/world/*.png` must be included with the addon. Source image ownership and
credits remain HorizonXI Wiki / Remapster / Square Enix / FFXI Atlas.

## Validation and evidence

Python with Pillow and `lupa` (LuaJIT 2.1) and `luacheck` are available in this
workspace. Runtime itself needs neither Python nor model/network access.

Run checks appropriate to the change; these commands do not launch agents:

```powershell
python addons/atlas/tests/verify.py
python addons/atlas/tests/ui_smoke.py
python addons/atlas/tests/test_world_runtime.py
python addons/atlas/tests/test_pois.py
python addons/atlas/tests/test_hotspots.py
python addons/atlas/tests/test_horizon_import.py
python addons/atlas/tests/test_expansion.py
python addons/atlas/tests/test_annotations.py
python addons/atlas/tests/test_world_art_export.py
```

`test_expansion.py` and `test_pois.py` intentionally regenerate their outputs to
check deterministic offline builds. Geometry/asset tests use local source caches
and the installed game; they are not fully portable synthetic-only suites.

Lua lint command used:

```powershell
luacheck addons/atlas/src addons/atlas/atlas.lua --no-max-line-length --globals addon ashita AshitaCore GetPlayerEntity GetEntity ImGuiMouseCursor_Hand ImGuiCond_FirstUseEver ImGuiWindowFlags_NoScrollbar ImGuiWindowFlags_NoScrollWithMouse ImGuiChildFlags_None ImGuiCol_WindowBg ImGuiCol_Button ImGuiCol_ButtonHovered ImGuiCol_ButtonActive ImGuiCol_FrameBg ImGuiCol_PopupBg
```

Last deterministic expansion and POI iteration passed all 9 test suites (`verify.py`,
`ui_smoke.py`, `test_world_runtime.py` (3), `test_pois.py` (4), `test_hotspots.py` (4),
`test_horizon_import.py` (5), `test_expansion.py` (5), `test_annotations.py` (3),
`test_world_art_export.py` (3)) and full source lint (12 files, 0 warnings/errors).

Specific checked behaviors:

- All native map-table entries and 616 original/installed HD DAT images;
  malformed images and LuaJIT compilation.
- 726 reviewed/source-correlated route directions and 682 unique imported polygon
  endpoint clicks through real UI callbacks; history, arrival focus and editor saves.
- Passive region names, outward scrolling from every supported map, relative
  world centering, and party/alliance toggles.
- Texture pages compared against the master at all detail levels; pointer zoom,
  culling, one upload/frame, gesture deferral, warm-cache reuse and 24-page budget.
- All 7 transport hubs and 9 native dock-click destination flows, including
  world-only destinations and category filtering.

Offline preview command:

```powershell
python addons/atlas/tests/ui_smoke.py --preview-dir C:/Users/bread/.codex/visualizations/2026/11/01/01a1950b-2457-7720-a396-f987f59c8068/atlas-poi
```

That folder contains `atlas-conquest.png` (full world), `atlas-poi-jeuno.png`,
`atlas-poi-selbina.png`, `atlas-poi-sandoria.png`, and other canvas previews.
Older `atlas-expanded` / `atlas-connected-runtime` previews show superseded UI.
These render actual draw calls offline; **they are not in-game screenshots**.

## Known gaps and sensible next work

1. **Live verification first when available.** Confirm world zoom smoothness and
   memory behavior, actual D3D8/XIPivot loading, native floor lookup, input, group
   movement/zoning and transport marker placement. No recent live pass has occurred.
2. Party/alliance tracking reads all 17 other roster slots on every draw.
   Entities must match server ID and roster zone, be rendered, and have a valid
   floor/map transform. Members use Boussole-style live `Movement.LastPosition`;
   the player uses `Movement.LocalPosition`. There is no timed position cache.
   Unavailable positions only contribute overview counts, never invented precise
   dots. Keep this behavior if investigating the user's earlier stale-location report.
3. The extension holds **16 native-floor aliases and 148 source candidates**.
   These are not necessarily 148 distinct missing connections: ambiguous pairings,
   protected directions and excluded transport candidates occur in the report. Inspect
   `floor-matches.json` and `connection-review.json` before guessing a new route.
4. Multi-floor dungeons whose replacement artwork reuses a shared composite overview
   across floors (e.g. `Korroloka Tunnel`, `Sea Serpent Grotto`, `Temple of Uggalepih`,
   `Ifrit's Cauldron`, `Quicksand Caves`, `Kuftal Tunnel`) or lacks an era-native ink
   match (`Uleguerand Range` map 2, `Garlaige Citadel` maps 2–4, `Labyrinth of Onzozo`)
   remain held in `floor-matches.json` rather than lowering similarity margins. Floor
   tabs remain available for all accepted maps.
5. `Port Windurst`, `Kazham`, and `Mhaura` are now charted native maps, and `Port
   Windurst` and `Kazham` have native dock markers projected from wiki boarding pulses.
   `Mhaura` (`14.json`) lacks a wiki connection pulse to `Selbina` (`161`), so its ferry
   endpoint remains a world-hub marker until a curated or wiki dock pulse is added.
6. Boats/airships are only the initial five-route set. Additional POI types,
   barge/Manaclipper services, persistent filter settings and optional schedules
   are possible later work, not completed features or established user requirements.

Do not describe source-matched links as proven Horizon behavior or offline
performance checks as proof that the user's in-game lag is solved. The current
handoff request adds documentation only; there is no pending requested code change.
