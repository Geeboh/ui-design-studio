# Coverage

## Initial inventory

| Measure | Count |
| --- | ---: |
| Eligible UTF-8 files | 141 |
| Binary/non-UTF-8 gaps | 10 |
| Acknowledged exclusions | 12 |
| Nested repository boundaries | 0 |
| Existing docs/documenter pages before publication | 0 |

Source snapshot: 40f3ff4151dfb62aa2f79001641057c0d7e4305bcdd7a66646a1f62af8280213. The inventory is authoritative for exact file hashes and paths.

## Gaps and exclusions

The ten gaps are three historical ZIP archives and seven PNG screenshots. The scanner cannot treat their binary content as UTF-8 source. Their names and sizes are recorded in .documenter/inventory.json.

The twelve exclusions are ignored/cache/runtime paths: __pycache__, .pytest_cache, .ruff_cache, .ui-design-studio, .venv, and related child paths. They are not part of the eligible denominator.

## Review boundaries

The review distinguishes source-file review, page review, documented mappings, supported claims, and declared symbols. Symbol records are not an exhaustive parser inventory. Existing human-authored pages under docs/ remain protected and were reviewed as source material rather than replaced.

After publication, rescan before recording current page hashes. Normal and strict checks are separate: strict can remain incomplete when binary gaps or open unknowns are explicitly recorded.

Sources: .documenter/inventory.json, Documenter references/coverage.md and operations.md.
