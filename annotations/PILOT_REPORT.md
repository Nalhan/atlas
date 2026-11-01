# Atlas annotation pilot

23 maps across Zulkheim, Norvallen and Fauregandi.

| Result | Count |
|---|---:|
| Proposed passages | 25 |
| Accepted after review | 25 |
| Accepted with corrections | 25 |
| Rejected | 0 |
| Needs more evidence | 0 |
| Pending | 0 |
| Worker unresolved observations | 31 |

Two smaller-model regional workers ran in parallel with an independent checker.
Reviews are bound to candidate hashes. Only accepted records are compiled.
No in-game traversal verification or measured provider billing is claimed.

The original Ronfaure seed remains explicitly `legacy_unreviewed`. Pilot records
are `artwork_reviewed`, a separate status from live traversal verification.

Mean exit-anchor shift on corrected accepted records: 18.96
reference pixels (512-pixel basis). This is a correction metric, not a global
accuracy estimate; accepted records and withheld records have different coverage.

Detailed findings: see pilot-report.json, reviews/decisions.json and sheets/index.html.

## What this trial established

The workers supplied useful connection candidates, but every final accepted record
needed some checker correction. Labels, leader arrows and physical passage mouths
must remain separate concepts in worker prompts and tools. The trial does not
establish that the smaller-model workflow is cheaper overall: checker effort and
provider usage must be measured in a future comparison.

Keep the independent checker for coordinate placement and floor identity. Reuse a
small reviewed example set to improve extraction, reserve a separate holdout set,
and compare accepted-map cost only after wrong-floor and missing-exit checks pass.
Raw worker inventories remain audit observations; only corrected reviewed passages
are used for runtime markers. Shared replacement artwork cannot establish native
floor connectivity; original geometry is required for those cases.
