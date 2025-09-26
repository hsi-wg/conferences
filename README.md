# HSI Conference & Workshop Website

This Quarto website aggregates INCOSE HSI Working Group Conferences and Workshops.

## Structure
- `_quarto.yml` – Site configuration & navbar
- `index.qmd` – Landing page with links to all events
- `about.qmd` – Background information
- `HSIYYYY/` – One folder per event year
  - `index.qmd` – Main event overview
  - `resources.qmd` – Resources, downloads, post-event material
  - `proceedings.qmd` (2024 only so far) – Lists paper pages in `proceedings/`
  - `proceedings/` – Individual paper `.qmd` files (templates now)
- `HSI2025/` – Current conference (adds `registration.qmd`, `schedule/`, `committee.qmd`)
  - `schedule/index.qmd` – Day listing
  - `schedule/dayN.qmd` – Day overview with listing of session pages in subfolder
  - `schedule/dayN/slot-template.qmd` – Template for each session (copy & customize)

## Adding Sessions (2025)
1. Copy the appropriate `slot-template.qmd` into the corresponding day folder.
2. Rename the file (e.g., `0900-keynote-ai-systems.qmd`).
3. Update front matter:
   - `title`: Session title
   - `author`: Speaker(s)
   - `abstract`: 2–3 sentence summary
   - `category`: Keynote / Talk / Panel / Workshop
4. Edit body: timing, room, bio.

## Adding Proceedings Papers (2024)
1. Duplicate `paper-template-1.qmd` with a descriptive filename.
2. Update metadata (title, authors, date, abstract, keywords).
3. Add sections as needed.

## Build
Render locally with:

```
quarto render
```

Or serve with live reload:

```
quarto preview
```

## Next Ideas
- Add taxonomy (categories/tags) for sessions.
- Add people profile cards & shared bios.
- Add automated schedule table with time zone conversion.
