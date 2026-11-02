# Review of Gemini's 18-region catalog — 2026-11-01

Reviewed snapshot: `7562987` (the initial Atlas repository commit), plus Gemini's
finished, uncommitted outpost/teleport additions checked on 2026-11-01.
The native map identities, generated data integrity and existing UI tests pass.
Three functional findings were identified (banner placement resolved in 0.8.3); the expanded catalog should not yet be described
as complete navigation coverage.

## Resolved P2: World banner rectangles did not consistently match the artwork

Atlas 0.8.3 imports the user's 53 selector corrections. Actual UI callbacks now
open the intended zones at all three artwork points below. The original review
evidence is retained for history; its placement finding is resolved.

The world anchor data needs a visual measurement pass. Tests currently click the
centers of the declared rectangles, so they do not detect rectangles below the
printed labels or a neighboring label swallowed by an earlier hit target.

Reproduced through the actual UI callbacks, at world zoom 6, using coordinates
measured on the native 8192-square artwork:

| Clicked printed label | World point | Actual behavior |
| --- | --- | --- |
| The Boyahda Tree | (7060, 4205) | Stays on world view; its hit area begins at y=4270 |
| The Shrine of Ru'Avitau | (5600, 1845) | Opens Ru'Aun Gardens |
| Western Outer Horutoto Ruins banner | (5430, 5145) | Opens West Sarutabaruta |

Source: `annotations/expansion/world-anchors.json`, especially entries 153, 178,
115 and 194. Regenerate regional/world metadata after correcting these boxes.
Some overlap is intentional around stacked ribbons, but the actual text must
remain reachable and open the named zone. Source artwork is the placement authority.

Visual review overlays are in:
`C:/Users/bread/.codex/visualizations/2026/11/01/01a1950b-2457-7720-a396-f987f59c8068/atlas-gemini-review/`
(`litelor.png`, `tulia.png`, `sarutabaruta.png`, plus other sampled regions).
These are offline inspection overlays, not game screenshots.

## P2: Multi-entrance crossings between different zone IDs disappear silently

`tools/expand_regions.py`, in `connections`, handles multi-pulse wiki pairings only
when both native maps share one zone ID. Across different IDs it requires exactly
one pulse at each end and otherwise skips the link without a held record.

Concrete case: wiki maps 10 and 15 (Lower Delkfutt Map 3 / Middle Delkfutt Map 1)
have three reciprocal staircase pulses each. Both floor aliases are accepted, but
there is no published Lower ↔ Middle passage, no directed candidate for the pair,
and no corresponding `wiki-10-15` / `wiki-15-10` held entry. The Middle/Upper tower
component is disconnected from the Lower tower's walking graph; floor tabs do not
cross their different native zone IDs. Gusgen also has disconnected floor groups.

Do not guess pairings to fill the gap: retain unresolved groups in the report,
then correlate/review their endpoints. Extend coverage checks beyond one reachable
map per region (`tests/test_expansion.py` currently only checks region membership).

## P2: The new POI data invents a Tu'Lia outpost

`annotations/poi/transport.json` declares `outpost-tulia` in Ru'Aun Gardens at
world coordinates (0, -540), with an outpost-teleport requirement. This publishes
both a world icon and a native-map marker for a service that does not exist.
The cited [Horizon outpost list](https://horizonffxi.wiki/Outpost_Teleportation)
lists 17 outpost destinations, including Tavnazia, and excludes Tu'Lia. The seed
currently contains 18 outposts because of this extra entry. Remove/hold this
unsupported record rather than presenting it as a confirmed teleport service.

The POI projection test computes its expectation from the same supplied
`world_xy`, so passing it establishes consistent projection rather than source
accuracy. Manually supplied coordinates need separate source evidence.

## Checks run

- `verify.py`: native entries and 616 original/installed HD DAT images pass.
- `ui_smoke.py`: 726 reviewed/source-correlated directions, 682 imported polygon
  endpoint clicks and 9 native transport dock flows pass.
- `test_expansion.py`: 5 tests pass, including identical offline rebuild outputs.
- `test_pois.py`: 4 tests pass.
- `test_horizon_import.py`: 5 tests pass.
- The independent artwork-click reproductions above fail the intended behavior
  despite the existing suites passing. No live game traversal was performed.

The original review made no source fixes. The later 0.8.3 selector handback resolves
the banner finding; the Delkfutt and unsupported Tu'Lia-service findings remain open.
The subsequent Besieged/Aht Urhgan expansion is implemented separately and covered
in HANDOFF.md. Combined verification after Gemini finished also passes: 882 DAT
images, 866 route directions, 801 polygon clicks and 38 native POI click flows.
These checks do not validate that the unsupported Tu'Lia service exists.
