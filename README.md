# Atlas 0.8.7: Connected world and Aht Urhgan

For continuation context, current limitations and build/check instructions, see
[HANDOFF.md](HANDOFF.md).

A connected map browser for Ashita v4: **world ↔ zone**.
Boussole does not need to be loaded. No startup scripts or other addons are changed.

## Open it

Run `/addon load atlas`, or `/addon reload atlas` if an older version is loaded.
Atlas starts hidden when loaded or reloaded. Open it with `/atlas` or `/atlas show`
to see your current zone and floor, centered on you. Areas outside this prototype fall
back to the world map. Area-name commands focus that part of the world canvas.
Opening Atlas brings it in front of ordinary addon windows. Menus opened afterward
can stay in front until you return to the map.

- Zoom and pan the world map, then click a supported zone banner to open its map.
  Region names are part of the artwork; there is no separate region screen.
- The complete connected world artwork supports pan and zoom up to native detail.
  At closer zoom, supported zone banners also open their maps directly.
- Click an exit to open its adjoining map, centered on the matching entrance.
- Click the map's exit mouths, arrows or printed numbers/letters. Invisible hit
  targets preserve the artwork; hover reveals a small outline and destination.
  The larger default rectangles cover the space between the physical exit and
  printed marker, with padding for the surrounding graphic. Overlapping areas
  open a passage chooser. Uncharted maps use plain text links.
- Nearby gates open a small passage chooser so overlapping hit areas remain usable.
- The world canvas uses the Horizon wiki's interconnected level-5 artwork,
  including printed zone outlines and dashed transitions.
- Breadcrumbs, Back/Forward, an area search, and short floor/district tabs handle browsing.
- Wheel zooms at the pointer; left drag pans. Scrolling outward past a zone's
  minimum zoom, right-clicking a zone, or choosing **World** opens its surrounding
  world area. After following an exit, this centers on the destination zone.
  Right-clicking the world zooms out around the pointer.
  Extra mouse buttons go Back/Forward. Locate centers on you; Fit restores the full view.
- Party / Alliance toggles are always available. Names and Reload maps are under `...`.
  On the world map, location pips sit beside zone labels at close zoom; region
  titles never carry a player or party marker.

## Points of interest

Boats, airships, outposts and teleports have distinct map icons. Toggle each
category independently under **... → Points of interest**. Region names remain passive.
Gemini's outpost and six teleport markers are included on the world and native
zone maps; click one for its requirements and location. The declared Tu'Lia outpost
is unsupported and remains an open review finding.
Outpost flags use live Conquest ownership: red for San d'Oria, blue for Bastok,
green for Windurst, amber for Beastmen, and gray until ownership is known. Hover
an outpost to see the owner. Atlas requests Conquest data on load and after zoning;
it does not infer control from geography.

- Routes include **Selbina ↔ Mhaura ↔ Whitegate ↔ Nashmau** and **Jeuno ↔ San
  d'Oria / Bastok / Windurst / Kazham**, plus **Bibiki Bay ↔ Purgonorgo Isle**
  by Manaclipper: eight routes across eleven hubs.
- Hover a world icon to see its destinations and highlight its transport links.
  Click it to open the port map; Jeuno's four services share one world icon.
- Fifteen distinct dock icons represent sixteen route endpoints. Click a dock
  to choose its destination; the destination map opens centered on its dock.
  Mhaura's shared boarding point offers both Selbina and Whitegate.
- Route details show the ticket/pass requirement. They do not report character
  pass ownership, fares or live departures. Map clicks only browse locations.

### Correct POI locations

Open `/atlas poi` or **... → Edit points of interest**. Drag a marker to move it;
drag empty space to pan. The world overview and zone-map positions are independent.
Shared docks move all their services together; world anchors are shared by town.

- Select any POI in the searchable editor list. **View zone** / **View world**
  finds it, including hidden markers.
- **Place on map** lets you click a new position on the current map. To correct a
  floor or zone, choose that map in Areas first, then place the selected POI there.
- **Use my position** places it at your character on the currently displayed zone
  map, when a matching position is available.
- **Hide POI** removes an incorrect entry from normal browsing; the editor retains
  it with a slash so you can show it again. **Undo POI** reverses a change.
  **Reset POI** restores the selected world anchor or zone entry to its shipped value.
- **Save POIs** saves your changes. **Done editing POIs** saves and leaves the editor.
  **Copy corrections** saves and copies the corrections; paste them into chat to
  hand them back for review and inclusion in the addon.

Corrections reload automatically and also save on addon unload. The portable file is
`config/addons/atlas/poi-corrections.json` under the Game folder, with a `.bak` of
the preceding valid save. Generated source data and manual exit areas are separate.
Unsaved changes are marked in the editor. Right click cancels a placement or drag.

### Correct world zone selectors

The latest 60 saved selector corrections are included as shipped defaults.
Purgonorgo Isle has its own banner selector, opening Bibiki Bay Map 2.
Generated zone names use Georgia Bold lettering that scales with the map zoom
(10–24 px), with wrapped long names and matching measured hit areas. Labels shrink
on wider views and cap their size at close zoom to leave room around nearby features. The Windows font is loaded once when Atlas loads;
if unavailable, enlarged default lettering is used.

Open `/atlas selectors`, **... → Edit world zone selectors**, or **Zone selectors**
from the POI editor. Search for a zone in the selector list; choosing it centers
the world on its click area. This works for both the main world and Besieged.

- Drag a box to move its click area, or drag a corner to resize it.
- **Draw selector** lets you draw a replacement box around the printed zone name.
  Drag empty space to pan; wheel zooms; right click cancels a drag/draw.
- **Undo selector** reverses a change. **Reset selector** restores the shipped box.
- **Copy selectors** saves and copies the corrections; paste them into chat to
  hand them back. **Done with selectors** saves and returns to normal browsing.
- **POIs** switches back to POI editing. POI icons are hidden while editing zone
  selectors so they cannot intercept clicks. Region names remain passive.

Changes apply immediately to zone selection and the world return camera. The
existing printed map artwork stays in place; supplementary Besieged labels follow
their selector centers. The separate save is
`config/addons/atlas/world-selectors.json`, with a `.bak` of the last valid save.
The addon loads it automatically and saves pending changes on unload.

`src/pois.lua` indexes categories, locations and links independently of walking
exits. Additions are declared in `annotations/poi/transport.json`; the offline
`tools/build_pois.py` projects cached wiki boarding pulses through the installed
native map transforms into `data/pois.lua`. World anchors identify towns and are
measured on the connected artwork. `annotations/poi/build.json` retains source
links and fingerprints. No additional POI textures or runtime
network requests are needed. Run:

```text
python addons/atlas/tools/build_pois.py
python addons/atlas/tests/test_pois.py
```

Route references: [Port Jeuno](https://horizonffxi.wiki/Port_Jeuno),
[Mhaura](https://horizonffxi.wiki/Mhaura),
[San d'Oria–Jeuno Airship](https://horizonffxi.wiki/San_d%27Oria-Jeuno_Airship) and
[Airship pass for Kazham](https://horizonffxi.wiki/Airship_pass_for_Kazham).

Commands: `/atlas`, `/atlas show`, `/atlas hide`, `/atlas world`,
`/atlas ronfaure`, `/atlas zulkheim`, `/atlas norvallen`, `/atlas fauregandi`,
`/atlas gustaberg`, `/atlas derfland`, `/atlas valdeaunia`, `/atlas vollbow`,
`/atlas qufim`, `/atlas aragoneu`, `/atlas kolshushu`, `/atlas sarutabaruta`,
`/atlas litelor`, `/atlas tulia`, `/atlas kuzotz`, `/atlas elshimo_lowlands`,
`/atlas elshimo_uplands`, `/atlas tavnazian_archipelago`, `/atlas besieged`,
`/atlas here`, `/atlas edit`, `/atlas poi`, `/atlas selectors`. Unload with `/addon unload atlas`.

## Multi-region deterministic expansion

Fourteen expansion regions (**Gustaberg, Derfland, Valdeaunia, Vollbow, Qufim,
Aragoneu, Kolshushu, Sarutabaruta, Li'Telor, Tu'Lia, Kuzotz, Elshimo Lowlands,
Elshimo Uplands, and Tavnazian Archipelago**) add **196 native maps and 338 passage
pairs**, including Bastok, Jeuno, Windurst, and Kazham districts. This Middle Lands set
has **236 map entries and 394 passages** across **18 regions**, with **596 published
polygon click areas** in `data/expanded_hotspots.lua` (plus **117** in
`data/wiki_hotspots.lua`). Their zone banners are clickable on the continuous world
map. Existing reviewed passages and manual click-area adjustments retain their behavior.

## Aht Urhgan / Besieged

The installed game's **Besieged** menu map (`ROM/161/34.DAT`, file ID 53416) is
displayed beside the existing world artwork. `/atlas besieged` centers that sheet;
zoom in to see clickable zone labels. Region names remain passive. Labels are
overview anchors grouped by region, not a geographic stitch of the zone maps.

The expansion adds all **129 validated native maps** in the original Treasures
map block, **9 reference charts** (Talacca Cove and eight Nyzul Isle layouts), and
four explicitly uncharted locations (Jade Sepulcher, Navukgo Execution Chamber,
The Ashu Talif and Hazhalm Testing Grounds). Its six groups are West Aht Urhgan,
Mamool Ja Savagelands, Halvung Territory, Arrapago Islands, Ruins of Alzadaal and
Western Aradjiah's sea routes. There are **70 accepted zone connections**, including
explicitly labeled runic-portal and reference-map links.

The combined browser now contains **378 entries**: 364 native maps, 9 reference
charts and 5 uncharted areas, with **464 zone connections**. Reference charts do
not claim native floor identification or precise player positions. Instanced and
uncharted areas with no supported entrance evidence remain without guessed links.

Sources and held cases are in `annotations/aht-urhgan/`. The native inventory is
independent of wiki alias matching: uncertain aliases hold connection tagging,
not access to installed maps. Whitegate's identical-art native variants are
disambiguated by the installed transforms and the pinned Al Zahbi zone line.
Mhaura's previously missed dock is explicitly supplied by the wiki's shared
`multiple.links` ferry record. Source correlation is not live Horizon verification.

```text
python addons/atlas/tools/expand_aht_urhgan.py fetch
python addons/atlas/tools/expand_aht_urhgan.py build
python addons/atlas/tools/build_world_art.py
python addons/atlas/tools/build_pois.py
python addons/atlas/tests/test_aht_urhgan.py
```

`fetch` caches public inputs; subsequent builds run offline. Reference image
fingerprints/credits are in `assets/references/SOURCES.json`. The Besieged base is
read from the installed game at runtime, preserving normal DAT redirection.

The review of Gemini's preceding definitions is recorded in
[`GEMINI_REVIEW.md`](annotations/reviews/GEMINI_REVIEW.md). Its Middle Lands banner
placement finding is resolved by the user's selector handback. Delkfutt connectivity
and the unsupported Tu'Lia outpost remain open; the Aht Urhgan expansion does
not claim to fix them.

The expansion uses cached wiki entrance data and pinned LandSandBoat zone-line
records, without agents or model calls. Native floor aliases require validated
installed DAT identities and unique artwork matches after removing shared grid
and parchment pixels. Connections require reciprocal endpoints with unambiguous
pairing. Server coordinates supply separate exit and arrival positions; uniquely
paired wiki links provide stairs and a fallback when server positions disagree.
Intercity transport links and reverse directions of existing curated drops are
excluded. Public source correlation is not in-game Horizon traversal verification.

Sixteen native-floor aliases and 148 directed source candidates remain held, with reasons
in `annotations/expansion/floor-matches.json` and `connection-review.json`.
Multi-floor dungeons whose replacement artwork reuses a shared composite overview image
 across multiple floor indices (or where era-native DATs have no unique ink match) are
held rather than guessed. Some mapped floors, including Castle Zvahl Keep's final floor,
still lack an accepted connecting exit; floor tabs remain available. Printed
regional-banner positions are measured on the artwork; the floor/exit matching is
deterministic.

To reproduce the expansion from the Game directory:

```text
python addons/atlas/tools/expand_regions.py fetch
python addons/atlas/tools/expand_regions.py build
python addons/atlas/tools/import_horizon.py fetch
python addons/atlas/tools/import_horizon.py build
python addons/atlas/tools/build_world_art.py
python addons/atlas/tests/test_expansion.py
python addons/atlas/tests/test_world_runtime.py
```

`fetch` reuses cached sources. Builds verify fingerprints and work offline;
`build_world_art.py` uses the full-resolution export described below. The extension
is generated separately in `data/expansion.lua`, `data/expanded_hotspots.lua` and
`data/expanded_regions.lua`, preserving the original reviewed catalog and evidence.
`annotations/expansion/REPORT.md` records counts, source hashes and held cases.

## Adjust exit click areas

Open a zone, then choose **... → Edit exit areas**, or run `/atlas edit`.
The selected exit has a highlighted rectangle and four corner handles.

- Choose an exit from the list, or click its area on the map.
- Drag the box to move it; drag a corner to resize it.
- Choose **Draw area**, then drag around the map label, arrow or other graphic.
  Right click cancels an unfinished gesture. Dragging empty space still pans.
- **Reset area** restores the selected exit's imported/default area. **Undo** reverses
  the latest completed edit, including Reset.
- **Save** keeps your adjustments; **Done** saves and leaves edit mode. Pending
  changes are also saved when the addon unloads.

Adjustments apply immediately and are shared across characters on this installation.
They are stored in `config/addons/atlas/exit-areas.json`, separately from generated
map/connection data, with the previous valid save in `.json.bak`. This file can be
copied or shared for review. Coordinates follow the map as you zoom or pan.
Editing a click area does not change a connection, its physical entrance, its
one-way restriction or the point shown when arriving from another map.

## Deterministic wiki/server import

`tools/import_horizon.py` reads JSON records embedded in the wiki's public map
module, without executing downloaded JavaScript. The cached source contains 423
maps. A 36-map baseline crosswalk (covering Ronfaure, Zulkheim, Norvallen, and
Fauregandi) maps wiki IDs to native floors, handles both world-coordinate and basic
256-pixel maps, and converts their connection polygons to Atlas's 512-pixel
reference (`117` published baseline endpoint areas in `data/wiki_hotspots.lua`).

Only unambiguous matches to existing allowed passages add runtime click areas.
Extra entrances, count mismatches, shared polygons and unknown targets remain in
`annotations/imports/horizon/candidates.json`. Imported shapes supplement the
physical entrance targets. Your editor rectangles take priority, and Reset
restores the imported/default coverage. The import does not change connection
directions, physical entrances or arrival positions.

The same pilot parses 17 zone files from a pinned public LandSandBoat commit into
directed candidates with source/arrival coordinates. Floors with multiple possible
maps require a clear wiki-marker match; unresolved floors are retained explicitly.
Public server behavior is not automatically treated as Horizon verification.
See `annotations/imports/horizon/REPORT.md` and `report.json` for measured coverage.

```text
python addons/atlas/tools/import_horizon.py fetch
python addons/atlas/tools/import_horizon.py build
python addons/atlas/tests/test_horizon_import.py
```

`fetch` caches public source files; `build` runs offline and checks their hashes.
The generated click areas are in `data/wiki_hotspots.lua`. Regional crops and
connection diagrams remain authoring references in `data/regional_art.lua`,
`assets/regions/` and `data/regions.lua`; they no longer form a separate runtime
screen. The world builder reuses their measured banner positions, area bounds
and supplementary labels. Attribution and tile fingerprints are retained in
`assets/regions/SOURCES.json`. The addon makes no network requests.

The closer interconnected-zone artwork starts at native level **5**. A separate
full-resolution authoring export is available with:

```text
python addons/atlas/tools/export_world_art.py --zoom 5
python addons/atlas/tests/test_world_art_export.py
```

This caches the 1024 source tiles and assembles an 8192 × 8192 PNG without
resampling, plus a smaller viewing copy, overview and offline pan/zoom viewer at
`exports/horizon-connected-z5/view-map.html`. The manifest retains tile coordinates,
source hashes and the world-to-pixel transform. This master shows the actual zone
outlines and dashed connecting routes. Runtime texture pages use this same
level-5 layer. The giant master itself is not uploaded as a
single game texture. Exports and source-tile caches are local artifacts.

The runtime world view now uses that complete master through a four-level texture
pyramid: 85 bounded 1024 × 1024 pages in `assets/world/`, described by
`data/world_art.lua`. Lower levels downsample the same connected artwork so its
geometry never changes when zooming. Only visible detail is requested, with a
coarse complete map behind it. Fine tiles wait until scrolling/panning has paused
for 120 ms, then load at most one per frame, nearest the viewport center first.
A cache retains up to 24 recently used pages (about 96 MiB with one mip level),
including while viewing a zone, so returning to warm zoom levels avoids repeated
texture creation. Older pages are released as the cache fills; unloading releases
all pages. The loader requests a single mip level because the pyramid already
provides detail levels. Native detail remains unscaled in
the highest level. The original Conquest DAT is a fallback if an asset fails.
The source manifest is `assets/world/SOURCES.json`. No runtime network access is
needed. Rebuild the pyramid with `python addons/atlas/tools/build_world_art.py`.

## Annotation pipeline and pilot

The original reviewed catalog has **40 map entries and 56 passages**, comprising
the original 31 passage seed and 25 artwork-reviewed connections. The adjacent-region
extension is appended at runtime. Each map's outward action centers the world
camera on that zone's neighborhood, preserving the previous world zoom when useful.

The authoring pilot used two `gpt-6-luna` regional workers in parallel and an
independent checker. It grew from 20 to 23 maps after inspection revealed additional
native-floor variants. Original-client PNGs are supplied alongside replacement
artwork because Ordelle, Eldieme and Fei'Yin replacements reuse complete cave images
for native floors that can contain only an isolated apparatus spur.

All 25 final accepted proposals required checker corrections. This trial is useful
evidence for the workflow, not proof of model cost savings or unchecked accuracy.
31 worker unresolved observations and 18 independent omission/coverage findings
remain in the authoring records; inventories are audit-only and are not published
as marker coordinates. The original seed is labeled `legacy_unreviewed`; new
records are `artwork_reviewed`, never traversal-verified.

Authoring files are under `annotations/`: `manifest.json`, `seed.json`, job packets,
isolated worker candidates, independent inventory and hash-bound decisions.
Passages carry separate exit, printed-badge and arrival-focus coordinates, local
badge codes, disconnected component IDs, direction and evidence. Only independently
accepted records reach `data/catalog.lua`; generated boards are in `data/regions.lua`.
Workers do not edit runtime Lua.

Run from the Game directory (Python with `lupa` and Pillow):

```text
python addons/atlas/tools/annotations.py prepare
python addons/atlas/tools/annotations.py check
python addons/atlas/tools/annotations.py build
python addons/atlas/tools/annotations.py sheets
python addons/atlas/tools/annotations.py report
```

`prepare` creates local artwork packets and jobs. Assign each job according to
`annotations/CONTRACT.md`; use a separate reviewer for `reviews/decisions.json`.
`check` rejects invalid geometry, self-approval, incomplete coverage, missing
evidence and stale reviews. Final reviews bind candidate files, the native/artwork
manifest, independent inventory and every accepted evidence image by SHA256.
Changed candidates or artwork require a fresh review before rebuilding.

`sheets` creates side-by-side endpoint review images and a local HTML index at
`annotations/sheets/index.html`. `PILOT_REPORT.md` and `pilot-report.json` report
outcomes and caveats. Generated packet/sheet images are excluded from source control
and are local authoring artifacts; runtime needs no models or authoring packets.
Exact provider billing was unavailable from the subagent tool and is not estimated.

An additional Antigravity trial ran two `gemini-3.8-flash-medium` jobs in parallel
through the installed `agy` CLI. Its 23-map input bundles contain native originals,
replacement artwork and floor metadata, without reviewed coordinates. The workers
returned 33 proposals, covering all 25 reference map pairs; 20 pairs put both exits
within 12 reference pixels. Five additional Ordelle stair links were independently
corrected and accepted as authoring records; three other proposals need more work.
This experiment remains separate from the original 56-passage catalog. See
[`REPORT.md`](annotations/experiments/flash38/REPORT.md) for the results and limits.

```text
python addons/atlas/tools/antigravity_trial.py prepare
python addons/atlas/tools/antigravity_trial.py run
python addons/atlas/tools/antigravity_trial.py evaluate
python addons/atlas/tests/test_antigravity_trial.py
```

`run` requires the normal authenticated `agy` desktop CLI. It pins the model,
uses read-only plan mode, requests structured output and caps concurrency at two.
Completed runs are protected against accidental reruns. `--retry-failed` retries a
failed run; `--resume-missing` resumes the same conversation if it ended without
annotations. A successful CLI exit alone does not establish a complete result.
`prepare` is for the initial setup; it refuses to overwrite inputs after a run.
Keep cumulative resumed-conversation usage separate from archived-turn totals.
Candidates, comparison and hash-bound review records are retained; copied input
images and full local CLI logs are excluded from source control.

## Included connections

The eight Ronfaure areas are represented, with floors grouped into zone banners:
West and East Ronfaure, Ghelsba Outpost (outside/caves), Fort Ghelsba,
Yughott Grotto (lower/upper), Horlais Peak, King Ranperre's Tomb (two primary maps),
and Bostaunieux Oubliette (three maps).

The San d'Oria hub includes North, South, Port and Chateau. Boundary zones
cover La Theine Plateau, Ranguemont Pass and Jugner Forest. The original slice includes
the separate Ronfaure crossings, the three Fort ↔
Yughott routes, Outpost cave entrances A/B/C, the city links, the Oubliette trapdoor
and one-way cliff exit, and the Tomb → enclosed Jugner connection. La Theine ↔
Jugner is also connected. Access restrictions and one-way travel appear on hover
and in the available directions. Map navigation does not move the character.

The world view shows interconnected artwork and passage links. Floors share a zone banner
and have explicit tabs in the zone view.
Horlais has no standard map, so its return exits appear on an uncharted view.

This is still a western-region prototype. It does not include clickable zones and
onward connections for the entire world, residential or battlefield instances, or the Tomb's
separate apparatus sub-map. Manually placed entrance anchors need an in-game
traversal pass before being treated as exact zone-line positions.

## Player, party and alliance

Green marks you, blue marks party, and purple marks alliance. Hover for names;
optional name labels are under `...`. Precise markers require a matching zone,
a matching native floor, a validated map-table entry, and a currently available
entity whose server identity matches the roster. All 17 other party/alliance
slots are inspected. Different zones, different floors, stale target indices,
unrendered entities and unavailable positions are not plotted as precise markers.

Roster members whose exact coordinates are unavailable still contribute to the
party/alliance counts beside their world-zone banner at closer zoom, when their zone is known. These
are area counts, not precise positions. Party and alliance entity positions are
read on every draw, following Boussole's live `LastPosition` approach; no timed
position cache delays movement or roster changes. Tracking pauses during zoning.
Positions outside the client's
available entities are not inferred or requested from the server.

## Map artwork and loading

Maps load from the installed client through Ashita's resource manager and CRT
`fopen_s`, allowing XIPivot to redirect reads. Original bitmap and HD DXT maps use
the same 512-pixel reference coordinates. Textures load on demand and are released
on reload/unload. Exit controls use invisible hit targets on all artwork, with no
added badges or buttons. Physical exit and printed-label anchors are both
clickable. A small outline appears only on hover.

The loader does not implement Boussole's custom-map calibration or redirect rules.
Zone-map artwork is read from the installed game. The connected world-map artwork
comes from the HorizonXI Wiki interactive map, whose credits include Remapster,
FFXI Atlas and Square Enix; its source tiles are documented alongside the asset.

## Validation

From the Game directory, with Python, `lupa` and Pillow installed:

- `python addons/atlas/tests/verify.py`
- `python addons/atlas/tests/ui_smoke.py`

The checks cover passage pairing/direction, arrival centering and history,
pointer-centered zoom, aspect-preserving crops, every curated native map-table
entry against the installed FFXiMain.dll, 616 original/HD DAT images, malformed DATs,
LuaJIT compilation, installed UI API names, and party/alliance identity, floor,
zone, despawn and consecutive-draw movement behavior. The real UI callbacks are also exercised through
an offline adapter: canvas clicks, clustered gates, route choices, area search,
floor tabs, panning, group toggles and printed-badge preservation.

The optional `--preview-dir PATH` on `ui_smoke.py` renders the actual canvas draw
calls with local map artwork. These are offline previews, not in-game screenshots.
Native Direct3D, XIPivot interception, floor calls and live input still require
an in-game pass.

`python addons/atlas/tests/test_annotations.py` separately exercises invalid and
unknown coordinates/maps, self-approval, candidate/manifest/artwork fingerprint
changes, incomplete independent coverage and compiled-output provenance. The UI
smoke test clicks every newly reviewed passage in every allowed direction and
checks its destination, home region and separate arrival focus.
The expansion tests check source hashes, native-floor confidence, reciprocal
evidence, protected one-way directions, transport exclusion, region reachability
and repeatable offline builds. World texture checks compare every page at every
detail level to the full master and exercise culling and pointer-centered zoom.
The UI adapter checks that region names are passive and clicks supported zone banners,
imported polygons and every new passage in both directions. It checks outward
scrolling from every supported map, relative world centering and preserved history.
Streaming checks enforce one upload per frame, no fine uploads during gestures,
cache reuse across zoom levels, eviction and the 24-page cache budget.
`python addons/atlas/tests/test_hotspots.py` checks larger/overlapping click areas,
draw/move/resize gestures, per-endpoint overrides, Undo, JSON persistence, backup
recovery and failed-save handling. The UI smoke test also draws and saves an area
through the real editor callbacks, then uses it after zooming and panning.

Suggested traversal: West → Outpost → cave A/B/C; Outpost → Yughott → Fort → upper
Yughott → Horlais; East → Tomb → enclosed Jugner; North → Chateau → Oubliette →
trapdoor → lower tunnels and West Ronfaure cliff exit. Check both Ronfaure crossings,
close city gates, group markers on multiple floors and Back/Forward arrival views.

## Files and references

`annotations/` owns source endpoints, badge codes, evidence and review decisions;
`data/catalog.lua` is generated, and `src/catalog.lua` supplies runtime lookups.
`src/region.lua` retains authoring crops and grouped map references.
`src/world.lua` selects visible detail, streams textures and locates zone neighborhoods.
`src/navigation.lua` owns history and viewport math. `src/client.lua` reads maps,
floors and group snapshots; `src/dat_image.lua` validates and wraps images.
`src/ui.lua` draws the interface. `src/hotspots.lua` owns click geometry and saved
overrides; `src/exit_editor.lua` handles on-map editing gestures.

Thanks to looney's [Boussole](https://github.com/loonsies/boussole) for the local
reference implementation of map-table signatures/layout, floor lookup,
CRT/XIPivot reads and world-to-map coordinates. Atlas imports no Boussole modules.
The original map entries were independently checked against this installed client.
Passage anchors and printed badge codes were checked against local
[Remapster](https://remapster.com/) / FFXI Vision artwork. The installed
[Ashita SDK](https://github.com/AshitaXI/Ashita-v4beta) annotations were used to
check UI and party/entity calls. Original artwork belongs to Square Enix.

Connection research: HorizonXI Wiki's
[Bostaunieux Oubliette](https://horizonffxi.wiki/Bostaunieux_Oubliette),
[King Ranperre's Tomb](https://horizonffxi.wiki/King_Ranperre%27s_Tomb),
[Chateau d'Oraguille](https://horizonffxi.wiki/Chateau_d%27Oraguille),
[Ghelsba Outpost](https://horizonffxi.wiki/Ghelsba_Outpost),
[Northern San d'Oria](https://horizonffxi.wiki/Northern_San_d%27Oria), and
[Southern San d'Oria](https://horizonffxi.wiki/Southern_San_d%27Oria).
