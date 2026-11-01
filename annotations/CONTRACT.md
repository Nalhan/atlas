# Atlas annotation pilot v1

All coordinates use the unrotated, top-left-origin 512 x 512 map reference.
Packet PNGs may be 1024 pixels; divide image coordinates by two. Do not infer
movement destinations from the printed text position.

Each worker owns one `annotations/candidates/JOB.json` file. Do not modify addon
Lua, other candidates, the manifest or reviews. Read the job, manifest and map
PNGs. Inspect both endpoint maps. Research Horizon-compatible evidence as needed.
Do not force an unknown exit into a guessed destination or floor.

Return JSON:

```json
{
  "schema_version": 1,
  "job_id": "zulkheim",
  "worker": "model/name",
  "inventory": [
    {"map": "latheine", "exits": [
      {"label": "Valkurm Dunes", "exit": [290, 410], "destination_hint": "valkurm"}
    ]}
  ],
  "passages": [
    {
      "id": "example-replace-this",
      "a": {"map": "latheine", "exit": [290,410], "arrival": [290,400],
        "badge": {"at": [290,410], "code": null, "printed": false}, "component": "main"},
      "b": {"map": "valkurm", "exit": [300,150], "arrival": [300,160],
        "badge": {"at": [300,150], "code": null, "printed": false}, "component": "main"},
      "direction": "both",
      "note": "",
      "evidence": [{"kind": "artwork", "source": "packets/latheine.png", "detail": "label and tunnel at south edge"}],
      "uncertainties": []
    }
  ],
  "unresolved": [{"map": "latheine", "label": "Exit outside pilot", "reason": "destination map not included"}]
}
```

The example coordinates are illustrative, not evidence. Inventory EVERY apparent
exit, including those that cannot be connected in this pilot. Pair only endpoints
that can be supported by inspected artwork and/or a cited source. Region-boundary
exits outside the manifest belong in unresolved. Keep one passage per distinct
entrance pair. Different printed A/1 badges are local to maps, not global IDs.

Use `direction: "a_to_b"` for a one-way route; never infer reversibility. Component
IDs distinguish disconnected areas of the same zone, notably enclosed Jugner.
`exit` is the actual passage location, `badge.at` is the printed glyph center,
and `arrival` is a nearby map-focus point. They can coincide if appropriate.
Codes must match visible artwork exactly. Report unsure codes as null.

No worker may mark its own annotations reviewed or traversal-verified. A separate
review file records independent findings, decisions, evidence and corrections.

## Checking and publishing

The checker first saves `reviews/independent_inventory.json` before inspecting
candidate files. Inventory every apparent passage, including omitted and out-of-
scope destinations. Original and replacement images are both available; a reused
replacement image does not prove that a native floor contains its depicted exits.

After workers freeze their candidates, save `reviews/decisions.json`:

- `schema_version: 1`, `reviewer`, `independent_inventory` path.
- `candidate_sha256`: job ID to exact candidate-file SHA256.
- `manifest_sha256`, `independent_inventory_sha256`.
- `packet_sha256`: every accepted artwork evidence path to exact PNG SHA256.
- `decisions`: one item for every candidate, keyed by `job_id` and `id`, with
  `decision` (`accept`, `reject`, `needs_work`), `reason` and evidence.
- Optional `corrections` may update `a`/`b` exit, arrival, badge, component and
  label, plus passage direction or note. Accepted uncertainties need explicit
  `resolved_uncertainties`. Never silently erase a worker's uncertainties.
- Keep omissions and findings separately; they are not runtime marker records.

An acceptance with corrections publishes the corrected result. The source worker
file is preserved for comparison. Run check, build, sheets and report. A changed
candidate, manifest, independent inventory or accepted evidence image invalidates
the review; do not simply refresh its fingerprints without reviewing the changes.
No record in this pilot is marked live-traversal-verified.
