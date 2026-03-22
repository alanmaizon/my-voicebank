# Clip Naming Rules

Use one unique numeric ID per final clip.

Rules:

- Format IDs as six digits: `000001`, `000002`, `000003`.
- Match each filename to the `name` field in `raw/transcriptions.csv`.
- Use `.wav` for the source clip extension.
- Never rename a clip after alignment or note extraction has started unless you update every reference.
- If a take is replaced, assign a new ID and mark the old one in the QC files.
- Store reasons like `breathy`, `clipped`, `bad diction`, or `retake needed` in QC notes, not in filenames.

Examples:

- `000001.wav`
- `000142.wav`
- `001005.wav`
