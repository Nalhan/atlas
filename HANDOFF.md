# Atlas handoff — 2026-11-01

## Start here

The current addon is **Atlas 0.8.7**, an Ashita v4 / LuaJIT FFXI map browser.
The latest work reviewed Gemini's 18-region catalog, then added Aht Urhgan on the
installed Besieged map beside the existing world. Offline checks pass; live game
validation remains outstanding. Read the 0.8 continuation notes below before the
older baseline pipeline details.

- Game/workspace: `D:\Games\HorizonXI\HorizonXI\Game`
- Addon: `D:\Games\HorizonXI\HorizonXI\Game\addons\atlas`
- Shell: PowerShell. Run the Python commands below from the Game directory.
- Reload in game: `/addon reload atlas`. Open/toggle: `/atlas`.
- [README.md](README.md) describes current controls, source pipelines and credits.
- The Game root is not a Git repository, but `addons/atlas` now is. Gemini created
  initial commit `7562987`; the 0.8 changes are uncommitted. No new PR or deployment
  was created during the review/Aht Urhgan work.

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
4. Atlas starts hidden on load/reload. Open `/atlas` / `/atlas show` to the player's current zone/floor by default,
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
| Map entries | 378: 364 native, 9 reference-only charts, 5 uncharted |
| Zone connections | 464, including existing one-way, runic-portal and reference links |
| Original catalog | 40 maps / 56 passages: 31 legacy seed + 25 artwork-reviewed (`117` baseline polygon click areas) |
| Middle Lands extension | 196 maps / 338 reciprocal passage pairs (`596` expanded polygon click areas) |
| Aht Urhgan extension | 129 native maps + 9 reference charts + 4 uncharted areas / 70 connections |
| Region groupings | 18 Middle Lands groups plus six Aht Urhgan groups. Original groups: Ronfaure, Zulkheim, Norvallen, Fauregandi, Gustaberg, Derfland, Valdeaunia, Vollbow, Qufim, Aragoneu, Kolshushu, Sarutabaruta, Li'Telor, Tu'Lia, Kuzotz, Elshimo Lowlands, Elshimo Uplands, Tavnazian Archipelago; cities grouped with neighboring areas |
| Full world artwork | Original 8192² artwork plus Besieged sheet to its right; canvas 12928 × 8192 |
| Interactive zone coverage | 24 groups. Middle Lands holds 16 aliases / 148 source candidates; Aht Urhgan holds 22 aliases / 74 candidates. Held aliases do not hide validated Aht native maps. |
| Transport POIs | 8 routes, 11 world hubs, 16 native endpoints represented by 15 dock icons |
| Other POIs | Gemini's 18 declared outposts + 6 teleports; combined 35 world markers and 40 native endpoint records. Tu'Lia outpost is unsupported (review finding). |

The extension also adds connections between previously supported regions and newly
added regions across the continent.

### Current points of interest

- Ferry: Selbina ↔ Mhaura.
- Airships: Jeuno ↔ San d'Oria, Bastok, Windurst and Kazham.
- Jeuno's four services share a world icon; its zone map has four dock icons.
- Hover world icons for destinations and route lines. Click a supported hub to
  open its port map. Click a zone dock icon for destination choices.
- All current transport destinations have native dock markers. Mhaura's shared
  boarding point offers Selbina and Whitegate; Whitegate also connects to Nashmau.
  The importer now reads the wiki's `multiple.links` record instead of incorrectly
  treating Mhaura's dock as missing. BASIC pixel pulses and world-coordinate pulses
  are handled separately.
- Independent Boats / Airships / Outposts / Teleports filters are under
  `... → Points of interest`. Gemini finished the 18 outpost and six teleport
  additions during the Aht Urhgan work; their importer, icons, popups and tests
  were preserved and checked together with the new ferries.
- Ticket/pass requirements are informational. There are no live schedules, fares,
  pass-ownership checks, travel automation or character movement.
- Manaclipper links Bibiki Bay Sunset Docks to Purgonorgo Isle. Sightseeing loops,
  barges and other ferry services remain future work.
- Transport is separate from the walking passage graph. Do not import airships as
  ordinary walking exits while expanding map connections.

## 0.8.7 Zone-only location pips and corrected nation colors

- The player pip formerly shown on the region title at world zoom below 2.5 is
  removed. Player, party and alliance pips appear only beside zone labels when
  those labels are visible. Their anchors use corrected selector bounds, so manual
  zone-label placement moves the pips with the label. Smoke coverage checks that
  overview region titles have no pip and a close-up corrected zone label does.
- ImGui packed draw colors are ABGR. Corrected all Conquest swatches after visual
  preview exposed the earlier channel reversal. San d'Oria is now a saturated red
  (#E63B49); Bastok is blue, Windurst green, Beastmen amber, unknown gray.
  The test checks red-channel dominance in the packed color, and the offline
  outpost-only world preview was inspected.

## 0.8.6 Conquest outpost colors and map window order

- `src/conquest.lua` reads the live incoming `0x05E` Conquest report. It uses the
  19-region order, zero-based `0x1D` offset and four-byte stride documented in
  the [HorizonXI-compatible Tally addon](https://github.com/Mr-Sithel/tally/blob/main/tally/tally.lua).
  Owner byte 1/2/3/4 maps to San d'Oria/Bastok/Windurst/Beastmen. Atlas sends the
  standard four-zero-byte `0x05A` request once after load and after zoning, using
  Ashita's delayed task facility. Before a valid response, outpost flags are gray.
- World and zone outpost flag icons use red/blue/green/amber for the four owners.
  Hover and click popups name the owner; the Outposts filter tooltip explains the
  colors. Tu'Lia stays gray because its outpost record is unsupported, even though
  the Conquest report has a Tu'Lia region slot. Tavnazia uses region slot 19.
- Opening Atlas calls `imgui.SetNextWindowFocus` once before its next `Begin`, so
  it rises above ordinary addon windows without retaking focus every frame from
  configuration dialogs opened afterward. The actual cross-addon order still
  needs a live client check, especially with addons that force focus each frame.
- Fixed the POI build manifest's count of map-keyed correction tables: the prior
  Lua `#` operator reported zero for 29 world and one zone correction even though
  the generated POIs had their corrected positions. It now records 29 and one.
- Offline smoke verifies packet decoding, colors, neutral/zone reset, request
  payload and one-time window focus. The full UI smoke and Lua lint pass.

## 0.8.5 Smaller labels and latest editor handbacks

- Supplemental Georgia Bold zone labels now range from 10 to 24 px in 2 px
  increments. The reference size is 16 px at 0.34 screen pixels per world pixel:
  approximately 10 px at the first clickable world zoom (2.5), 16 px at zoom 4,
  and the 24 px cap at zoom 6. Drawing, measured automatic hit areas and editor
  outlines continue to share the current size; exact manual rectangles stay exact.
- Imported the latest saved `config/addons/atlas/world-selectors.json` and
  `poi-corrections.json` through their validated deterministic importers. Immutable
  input snapshots are `annotations/world-selectors/handbacks/2026-11-01-user-latest.json`
  and `annotations/poi/handbacks/2026-11-01-user-latest.json`. The world correction
  layer now has 60 selectors (12 new/changed since the prior handback); the POI
  layer has 29 world positions (new Bibiki Bay and Purgonorgo Isle placements) and
  the same Ru'Aun Gardens stop correction. The two generated Lua datasets were
  rebuilt. Local editor saves and backups were left intact.

## 0.8.4 Zoom-scaled zone lettering

- Supplemental Georgia Bold zone names now follow the actual canvas scale, which
  includes zoom and viewport size. Reference: 20 px at 0.34 screen pixels per world
  pixel (roughly world zoom 4 in the standard window). Text ranges from 12 to 28 px
  in 2 px increments: wider views shrink it; close views cap its size while the map
  continues to spread apart. Printed artwork and passive region labels are unchanged.
- `map_labels.set_scale` runs before world selector interaction/drawing. Wrapping
  width scales with the font; drawing, automatic hit bounds and selector outlines
  all use the same per-size metrics. Exact manual selector bounds remain untouched.
- Measurement caches are keyed by the nine allowed sizes and title; zoom does not
  accumulate an unbounded set of font sizes or repeatedly add font objects. The
  font is still loaded once in the addon load event, outside drawing.
- UI smoke coverage clicks the visible label edge at zoom 2.5, 4, 6, 12 and 32,
  checks shrinking/growing/capping, metric-aligned bounds, balanced font state and
  the bounded cache. Existing editor, navigation, startup-hidden and boat flows pass.

## 0.8.3 Labels, selector handback and Purgonorgo

- Imported the user's 53 selectors exactly from
  `annotations/world-selectors/handbacks/2026-11-01-user.json` into the tracked
  corrections layer and rebuilt world metadata. Local config/editor saves were
  preserved. Independent artwork clicks for Boyahda (7060,4205), Shrine of Ru'Avitau
  (5600,1845) and western Outer Horutoto (5430,5145) now open the correct zones.
  The prior banner-placement review finding is resolved; Delkfutt multi-crossings
  and the unsupported Tu'Lia outpost finding remain open.
- `src/map_labels.lua` draws supplemental zone names in Georgia Bold at 20 px,
  wrapping at 180 px and measuring the actual wrapped text. The Windows font is
  added only in the load callback, outside frames; failure uses the enlarged default
  font. Hit testing and editor outlines use the same measurements. Explicit manual
  selector bounds remain exact. Original printed banners retain their artwork.
  Four Aht sea-route anchors were spaced farther apart to accommodate the larger type.
- Purgonorgo's printed banner is measured in
  `annotations/world-selectors/additions.json`. The world builder splits Map 2 from
  Bibiki's Map 1 selector and gives it explicit stable ID `zone-4-purgonorgo`.
  `world_selectors.id` accepts an explicit ID before falling back to native zone ID;
  multiple separately charted areas can share a native zone without losing edits.
  There are now 133 world selectors. World return focus follows the island's node.
- Added `manaclipper-bibiki-purgonorgo` to the POI seed. Both docks use the existing
  pinned reciprocal wiki pulses (82 ↔ 83), projected through their native transforms.
  The route requires a Manaclipper ticket/multi-ticket and the island sailing; no
  live schedule or character movement is implied. Transport stays separate from
  the walking graph. Total 8 transport routes, 11 transport hubs, 16 native transport
  endpoints / 15 distinct dock icons; with outposts/teleports: 35 world markers,
  40 native endpoint records / 39 native marker positions.
- UI checks cover enlarged label edges, font-stack balance and a single font load,
  the supplied banner fixes, Purgonorgo's world selector and all 40 dock/POI flows.
  Native/runtime, POI editor, world selector and deterministic Aht tests pass.
  Latest offline previews: `atlas-type-and-purgonorgo/` in the visualization folder,
  including `atlas-besieged-detail.png`, `atlas-bibiki.png`, `atlas-purgonorgo.png`.
  These are rendered draw calls, not in-game screenshots.

## 0.8.2 World selector editor

- `/atlas selectors`, `... -> Edit world zone selectors`, or the POI editor's
  `Zone selectors` button opens the new world mode. It covers all 132 zone selectors
  across the existing artwork and Besieged. Region names remain passive.
- `src/world_selector_editor.lua` supports searching/focusing selectors, drawing
  replacement boxes, moving and corner resizing, Undo, Reset, Save/Done and Copy.
  Blank-space pan and wheel zoom remain usable. Right click cancels a gesture.
  POIs and ordinary zone activation are suppressed in this mode. Modes save before
  switching; the `POIs` button returns to POI editing.
- `src/world_selectors.lua` uses stable `zone-<native zone ID>` keys. All current
  selectors have distinct zone IDs. Corrections affect hit testing and world return
  focus; they do not modify printed map artwork. Supplemental Besieged text stays
  centered on its box. Unedited Besieged labels retain screen-measured hit areas;
  an edited box uses the exact world-space bounds supplied by the user.
- User file: `config/addons/atlas/world-selectors.json` plus `.bak`. Startup/unload
  load/save it alongside (but separate from) POI and exit-area files. Malformed files
  are retained; a valid backup can be recovered. Copy selectors provides JSON for chat.
- Shipping: `python addons/atlas/tools/import_world_selectors.py FILE` validates and
  displays a handback. After reviewing, `--apply` merges it into tracked
  `annotations/world-selectors/corrections.json`, then rebuilds world metadata. The
  world builder reapplies this layer and records its fingerprint in the source
  manifest; no manual edits to generated Lua or source banner measurements are needed.
- `tests/test_world_selectors.py` covers scaled move/resize/draw, cancellation,
  world-return focus, Besieged default/manual geometry, backup/reload, invalid IDs
  and bounds, and shipping validation. Actual UI smoke tests cover draw/pan/travel
  isolation, copy/reload, and opening a zone through its corrected click box.
- The user POI handback has shipped as 27 exact world anchors plus one native
  marker. Zone-selector smoke tests hide POI overlays while testing banner clicks:
  a valid user-positioned POI can overlap a declared banner center. POI interactions
  are tested separately. Existing independent artwork-placement findings remain open.
- Offline checks pass; no agent-run in-game selector editing pass has occurred.

## 0.8.1 POI editor

- User handback `annotations/poi/handbacks/2026-11-01-user.json` was imported into
  `annotations/poi/corrections.json`: 27 world anchors and the Ru'Aun Gardens
  `outpost-tulia` native marker. All values retain the supplied precision. The normal
  POI build reapplies these as shipped defaults. Local config corrections and exit
  areas were left intact. This is a user location correction, not independent proof
  of the Tu'Lia service; retain the separate review finding unless resolved.
- `/atlas poi` or `... → Edit points of interest` toggles a separate POI edit mode,
  mutually exclusive with the exit-area editor. It blocks passage/POI travel while
  editing, preserves blank-space panning and pointer zoom, and keeps markers visible
  regardless of category filters. Hidden entries remain editable with a slash.
- `src/poi_editor.lua`: drag shared docks / world anchors, select/search any stop,
  click-to-place on the current world/zone map (including reassignment to a different
  native floor), use the matching player's position, hide/show, reset and Undo.
- `src/poi_edits.lua`: stable hub/stop IDs, independent world/native corrections,
  validation, snapshots, persistence and backup. Invalid files are kept and block
  saving when no valid backup can be read. Never overwrite this user's corrections.
- User file: `config/addons/atlas/poi-corrections.json`, plus `.bak`. Loaded at addon
  load; Save, Done, Copy corrections and unload save changes. Copy corrections uses
  the installed ImGui clipboard API, so the user can paste the JSON into chat.
- `src/pois.lua` applies local corrections to a copy of shipped data and reindexes
  markers/routes. Hidden services do not leave selectable transport links. Changes
  to shared world anchors do not move native docks, or vice versa.
- Shipping handback: save the received JSON somewhere in the workspace, then run
  `python addons/atlas/tools/import_poi_corrections.py FILE` to validate/display it.
  Review its positions/hidden flags; `--apply` merges it into tracked
  `annotations/poi/corrections.json` and rebuilds shipped `data/pois.lua`. The normal
  POI builder reapplies this reviewed layer deterministically and fingerprints it.
  Do not change source wiki pulses or reverse-engineer native coordinates for a
  correction already supplied in 512-pixel map coordinates.
- `tests/test_poi_editor.py` covers persistence/backup, malformed/unknown entries,
  coordinate-space isolation, reassignment, shared-dock drag, hiding/Undo, and the
  shipping build. `ui_smoke.py` also drives actual editor mouse/button callbacks,
  proves panning/travel isolation, and checks copied JSON and reloaded positions.
- No live in-game editor pass has occurred. Existing Gemini review findings remain
  pending; Hide POI allows the user to mark an unsupported entry in their handback.

## 0.8 continuation notes

- Review findings: `annotations/reviews/GEMINI_REVIEW.md`. Actual artwork clicks
  reproduce Boyahda Tree missing its target, Shrine of Ru'Avitau opening Ru'Aun
  Gardens, and western Outer Horutoto opening West Sarutabaruta. Lower → Middle
  Delkfutt's multi-pulse crossings are silently skipped. These findings are still
  pending; do not confuse passing declared-center UI tests with artwork accuracy.
  Final POI review also found an invented Tu'Lia outpost; the source lists 17
  destinations while Gemini declared 18. That record remains pending removal.
- New importer: `tools/expand_aht_urhgan.py fetch|build`. Inputs/reports are in
  `annotations/aht-urhgan/`; outputs are `data/aht_urhgan.lua`, `aht_hotspots.lua`
  and `aht_regions.lua`. It reuses deterministic source/geometry helpers from
  `expand_regions.py` without modifying the existing 236-entry catalog.
- All valid native Treasures map entries at indexes 294–431 are inventoried,
  independent of image-matching confidence. Whitegate floor variants have identical
  pixels but different transforms; one unique strong zone-line fit breaks the tie.
- Talacca Cove and Nyzul's eight charts use explicitly marked reference PNGs from
  cached wiki images (`assets/references/`). Reference-only entries use synthetic
  negative floor IDs for browsing; automatic native-floor selection skips them and
  precise actor positions are disabled. `src/client.lua` can load a definition's
  `asset` as well as native DATs. Four locations have no usable native/reference
  chart and remain explicitly uncharted.
- Besieged: file ID 53416, `ROM/161/34.DAT`, texture identity `m_ex3_rg`, 512².
  It is read through the existing native DAT loader at runtime. Placement/layout
  is in `annotations/aht-urhgan/layout.json`. This is a separate original-game
  overview sheet, not a georeferenced seamless zone-map stitch. The map has no
  printed zone names; supplementary labels and their hit areas are drawn together.
  Regions remain noninteractive. `/atlas besieged` focuses the sheet.
- `build_world_art.py` retains the original 85 pages and adds Besieged metadata,
  nodes, six region groups and passive labels. The canvas width is now 12928.
  Rebuild it after Aht catalog/layout changes, then rebuild POIs.
- Two ferry services were added: Mhaura ↔ Whitegate and Whitegate ↔ Nashmau.
  `src/pois.lua` groups collocated native endpoints so shared docks offer all
  destinations. Transport remains separate from walking connections. Conditional
  Whitegate ↔ Bhaflau passage is labeled as a runic portal.
- New checks: `tests/test_aht_urhgan.py` validates the original native inventory,
  Besieged identity/placement, reference fidelity/no fake native positions, shared
  ferry docks and repeatable offline builds. Existing suites cover 866 route
  directions, 801 imported polygon clicks and 38 native POI endpoint flows
  (14 transport + 24 outpost/teleport).
- Latest previews are in the writable visualization folder's `atlas-aht-urhgan/`:
  `atlas-conquest.png` (both sheets), `atlas-besieged-detail.png`,
  `atlas-whitegate.png` and `atlas-talacca.png`. Older preview folders show older UI.
- Live Direct3D/input/traversal and user-perceived performance are still unverified.
  Do not claim that held connections, the Gemini review findings, or every dynamic
  instance are solved just because native/reference artwork is available.

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
- World geometry uses top-left-origin **12928 × 8192 canvas pixels**. The original
  artwork occupies the unchanged 8192² area; Besieged is at (8512, 2304), size 4096².
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
python addons/atlas/tests/test_poi_editor.py
python addons/atlas/tests/test_world_selectors.py
python addons/atlas/tests/test_hotspots.py
python addons/atlas/tests/test_horizon_import.py
python addons/atlas/tests/test_expansion.py
python addons/atlas/tests/test_aht_urhgan.py
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

The preceding Middle Lands iteration passed all 9 test suites (`verify.py`,
`ui_smoke.py`, `test_world_runtime.py` (3), `test_pois.py` (4), `test_hotspots.py` (4),
`test_horizon_import.py` (5), `test_expansion.py` (5), `test_annotations.py` (3),
`test_world_art_export.py` (3)) and full source lint (12 files, 0 warnings/errors).

Specific checked behaviors:

- All native map-table entries and 882 original/installed HD DAT images;
  malformed images and LuaJIT compilation.
- 866 reviewed/source-correlated route directions and 801 unique imported polygon
  endpoint clicks through real UI callbacks; history, arrival focus and editor saves.
- Passive region names, outward scrolling from every supported map, relative
  world centering, and party/alliance toggles.
- Texture pages compared against the master at all detail levels; pointer zoom,
  culling, one upload/frame, gesture deferral, warm-cache reuse and 24-page budget.
- All 9 transport hubs and 38 native POI click flows (14 transport + 24 outpost/
  teleport), including shared docks, destination browsing and category filtering.
- Aht Urhgan's five-test suite also checks native inventory, reference fidelity,
  Besieged placement and repeatable offline generation. The combined runtime
  and native-map checks passed after Gemini finished editing.

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
4. The preceding Gemini review found incorrectly placed/overlapping Middle Lands
   world banners (now fixed by the 53-selector user handback) and a missing Lower → Middle Delkfutt connection group. These
   were reproducible despite passing declared-center tests. Delkfutt remains open;
   see the updated review report.
   Gemini's finished POIs also include an unsupported Tu'Lia outpost. Projection
   tests alone do not establish that a teleport service exists.
   The 16 held original aliases concern Uleguerand, Pso'Xja, Upper Delkfutt and
   Castle Oztroja, not every composite-map dungeon named in older handoff text.
5. Mhaura's shared ferry pulse is now supported; it is no longer world-only.
   Aht Urhgan retains 22 ambiguous wiki aliases and 74 held source candidates.
   All validated native maps remain browsable even when connection tagging is held.
6. Boats/airships currently include eight routes. Barges, sightseeing loops, additional
   POI types beyond the current outposts/teleports, persistent filters and optional
   schedules remain future work.

Do not describe source-matched links as proven Horizon behavior or offline
performance checks as proof that the user's in-game lag is solved. The original handoff request was followed by the Gemini review and Aht Urhgan
implementation described in the 0.8 continuation notes. Review findings remain open.
