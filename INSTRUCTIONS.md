# Project Continuation Guide

This document captures the essential knowledge needed to extend the Regatta Track Analysis project.

## Core Concepts
- **Primary focus**: analysing sailing GPX logs and presenting curated playback windows in static HTML (served from `docs/`).
- **Tooling**: Python utilities in `src/` handle GPX parsing and visualisation; interactive, client-side experiences live entirely in HTML/CSS/JS within `docs/`.
- **Data sources**: raw GPX lives under `data/` (general assets) and `docs/data/` (public artefacts). Keep sensitive or large originals outside the `docs/` tree until you are ready to publish.

## Key HTML Pages
- `docs/multi_boat_timeline.html` — flagship Leaflet-based viewer that can load up to three boats in sync.
  - Query params:
    - `windowStart` / `windowEnd`: `HH:MM[:SS]` strings interpreted in the browser's local time (matches GPX timestamps that include timezone info).
    - `speed`: optional playback multiplier (max 30).
    - `boats`: comma-separated track IDs (`rerata`, `boat_two`, `boat_three`) to load a subset. When omitted, all configured tracks load.
  - Boat names (UI):
    - `rerata` → “Olimpia 1” (`docs/data/rerata_26_oct.gpx`)
    - `boat_two` → “Olimpia 5” (`docs/data/2025-10-26-8_43.gpx`)
    - `boat_three` → “Olimpia 2” (`docs/data/2025-10-26-boat_three.gpx`)
  - Inline fallbacks: base64 GPX strings live in `docs/data/track-inline-data.js` under matching keys. Keep these in sync when adding new tracks.
  - Rendering notes:
    - When a window has no overlap with a boat’s timestamps, its polyline is hidden (to avoid ghost tracks).
    - Timelines and status cards derive from GPX timestamps; ensure files are sorted chronologically.
- `docs/races.html` — marketing-style landing page linking pre-defined windows into the multi-boat timeline.
  - Session 5 uses `boats=boat_two,boat_three` so Olimpia 1 stays hidden (no data after 13:31).
  - Update the hero copy if you change the number of curated sessions.
- Various single-race visualisations (e.g., `docs/2025-07-19-10_31_visualization.html`) are generated via `src/generate_track_html.py`.

## Adding / Updating Tracks
1. **Prepare GPX**: place raw files under `docs/data/`. For merged tracks (e.g. combining multiple devices), use a small Python script similar to the one in this repo to merge by timestamp.
2. **Publish file**: name GPX files with ISO-like identifiers (`YYYY-MM-DD-hh_mm.gpx` or descriptive slug).
3. **Inline fallback**: run `base64 < path.gpx` and embed the output inside `docs/data/track-inline-data.js` under a unique key. Maintain ASCII-only formatting.
4. **Register track**: update `TRACK_CONFIG` in `docs/multi_boat_timeline.html` (id, display name, colour, `gpxPath`, inline key).
5. **Optional**: extend the `boats` query parameter logic if you introduce new IDs (ensure new IDs are documented in this file).

## Adding New Race Windows
1. Decide on the `windowStart` / `windowEnd` times (local-time strings).
2. Update `docs/races.html` with a new `<article class="card">` block; keep voice short and action-oriented.
3. Link to `multi_boat_timeline.html` with the appropriate query parameters. Use `boats=` when you need to hide tracks with missing data.
4. Refresh the hero copy if the number of curated sessions changes.

## Styling & Assets
- Favicons and other shared assets live under `docs/assets/` (e.g., `north-star.svg`). Reference them with relative paths (no build step involved).
- Use subtle gradients and existing colour tokens defined in each page’s `<style>` block to maintain the design language.

## Dev Tips
- Work directly from the repository root; all docs are static and can be opened via `file://` locally (or served with a simple HTTP server for CORS safety when loading external tiles).
- Regenerate or adjust `docs/data/track-inline-data.js` carefully; it’s large, so append new entries rather than rewriting existing ones.
- Keep GPX timestamps in UTC when exporting, but let the browser interpret them in local time (current UI expectation).
- When merging timelines, ensure `windowStart`/`windowEnd` fall within the available data to avoid empty maps.

## Known Gaps / Future Ideas
- Automated build scripts for base64 inlining (currently manual).
- Add unit tests or linting for the JavaScript logic.
- Explore progressive loading for large GPX sets to reduce initial payload size.

Refer back to `README.md`, `FEATURES.md`, and `logic.md` for deeper implementation details.
