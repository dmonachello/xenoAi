# Candidate B: validation evidence files only

## Caller view

The command surface matches Candidate A, but reports live under `validations/<revision>/<run>.json` and meshes under `meshes/` without database rows.

## Advantages

- No SQLite migration.
- Reports remain directly inspectable.

## Costs

- Status and history require directory scans.
- Referential integrity, deduplication, and concurrent writes are weaker.
- A renamed, missing, or partial report can silently detach evidence from a revision.

## Red-flag screen

This creates a second ad-hoc index beside the revision database and weakens atomicity. It is acceptable for transient run logs, not as the authoritative validation record.
