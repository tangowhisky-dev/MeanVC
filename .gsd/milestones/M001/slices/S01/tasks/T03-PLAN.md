---
estimated_steps: 5
estimated_files: 3
skills_used: []
---

# T03: Strip Flet from DECISIONS.md, KNOWLEDGE.md, PROJECT.md

1. Read .gsd/DECISIONS.md — remove the old D001 narrative section entirely (D001 entry now only in the decisions table as PySide6).
2. Read .gsd/KNOWLEDGE.md — the Flet GUI section should now just be a note that Flet was considered but PySide6 was chosen; all Flet-pattern guidance (page.update, pubsub) removed. The PySide6 section is already present; remove the Flet section header and all Flet-specific bullets.
3. Read .gsd/PROJECT.md — update the DB location field to reflect data/meanvc.db; remove any remaining Flet references.
4. Read .gsd/DECISIONS.md — update D005 rationale to not mention Flet.
5. Verify: grep -n 'flet\|Flet' .gsd/*.md returns only lines that are legitimately historical cross-references (D001 superseded note).

## Inputs

- `.gsd/DECISIONS.md`
- `.gsd/KNOWLEDGE.md`
- `.gsd/PROJECT.md`

## Expected Output

- `KNOWLEDGE.md and PROJECT.md contain zero Flet references`
- `DECISIONS.md D001 section clearly marked superseded with one sentence explanation`

## Verification

grep -c 'Flet' .gsd/KNOWLEDGE.md .gsd/PROJECT.md | awk -F: '$2>0{fail=1} END{exit fail}' && echo 'No stale Flet refs'
