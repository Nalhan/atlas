# Antigravity Flash 3.8 annotation trial

Updated native-floor metadata and originals differ from earlier Luna inputs; not a controlled model-only comparison.

Results are compared against the existing independently reviewed map estimates. No experiment tags enter the addon automatically.

| Job | Proposed | Reference | Paired maps | Both exits within 12 px | Mean exit error |
|---|---:|---:|---:|---:|---:|
| zulkheim | 12 | 6 | 6 | 4 | 8.11 |
| north_east | 21 | 19 | 19 | 16 | 6.63 |

Coordinates use the 512-pixel reference. A paired-map match alone does not establish the correct entrance, floor, direction or component.
Both printed-badge anchors are within 12 pixels on 14 of 25 reference pairs. Badge placement still needs review.

## Additional proposals

- zulkheim: 5 accepted after artwork review (5 corrected), 1 need more work, 0 pending. See `reviews/zulkheim_novel.json`.
- north_east: 0 accepted after artwork review (0 corrected), 2 need more work, 0 pending. See `reviews/north_east_novel.json`.

The five corrected accepts are Ordelle stair links A–E. The F drop has transposed arrival focuses and an unverified direction; two Jugner/Landing proposals need paired entrance checks. These decisions do not publish tags or establish complete map coverage.

## Running the worker

Two isolated jobs used `gemini-3.8-flash-medium` through the installed `agy` CLI in read-only plan mode. Image reads were recorded. No reviewed-answer file access was flagged in the captured tool requests; this is a trace check, not a filesystem isolation guarantee.
The provider initially rejected numeric enums in the output schema; a bounded integer works. Each image-reading turn later ended without annotations after an optional command was denied. Both conversations were resumed once to return the final structured results. Exit code zero or status SUCCESS alone is not sufficient: require annotation_complete.
Usage in comparison.json is cumulative for each resumed conversation. Do not add archived-turn totals again. Billing/credit data were unavailable, so no monetary estimate is made.

Usage and image-tool trace summaries are in comparison.json; full agent events and requests are under runs/.
Runtime catalog and region data unchanged: True. No live traversal or provider cost saving is claimed.
