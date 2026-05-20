# Visualization

Use the visualization UI to generate canon candidates from a MIDI or MusicXML melody, inspect the score and piano-roll explanation, play the result, and download the generated artifacts.

## Install the visual extra

From the repository root:

```bash
uv sync --group dev --extra solver --extra visual
```

The `visual` extra installs the FastAPI server dependencies. The `solver` extra keeps solver-backed candidates available when `engine = auto` or `engine = solver`.

## Install frontend dependencies

```bash
cd web
pnpm install --frozen-lockfile
```

If `pnpm` is not installed globally, run the same command through `npx`:

```bash
cd web
npx --yes pnpm@latest install --frozen-lockfile
```

## Start the development servers

Run the API server from the repository root:

```bash
uv run canonize-web --output-root ./runs --host 127.0.0.1 --port 8000
```

Run the Vite dev server in another shell:

```bash
cd web
pnpm dev
```

Vite proxies `/api` to `http://127.0.0.1:8000`. Open the Vite URL, usually `http://127.0.0.1:5173`.

## Upload and inspect a melody

1. Select a `.mid`, `.midi`, `.musicxml`, `.xml`, or `.mxl` file.
2. Choose `Engine`, `Top K`, `Score profile`, `Chord policy`, and `Part policy`.
3. Click `Generate`.
4. Select a candidate in the candidate table.

The candidate view shows:

- Verovio-rendered score pages.
- Piano-roll note lanes with bar and beat grid lines.
- Playback controls and active-note highlighting.
- Score breakdown by category and rule.
- Musicality and composition analysis for phrase spans, cadence strength, and bass motion.
- Violation filters and linked piano-roll highlighting.
- Repair or solver actions for relaxed candidates.
- Download and render controls.

## Use composition assistance

Use `Phrase Polish` to search local variants for the selected candidate. Choose a bar range, a preset, and a mode:

- `Local polish` keeps the existing lock/rewrite controls.
- `Rewrite lower under fixed upper` keeps the leader fixed and searches a new follower line.
- `Rewrite upper above fixed lower` keeps the follower fixed and searches a new leader line.

The polish result is added to the candidate list and stored as an experiment in `Candidate Lab`.

Use `Feedback` when you want to start from plain text instead of choosing objective weights. Examples such as `cadence weak`, `bass too static`, `too repetitive`, and `too many leaps` translate into structured polish actions. Review the suggested action, then run it to create variants from the selected candidate.

Use the `Analysis` panel in the inspector to check the current candidate before and after edits. It shows phrase spans, the final cadence summary, and whether the lower voice is static, stepwise, or active.

## Download artifacts

The `Exports` panel downloads these files through the API:

- MIDI
- MusicXML
- `report.md`
- `results.json`
- `visualization.json`

The browser never reads local output paths directly. Downloads are served only from files registered in `artifact_index.json`.

## Render PDF, SVG, or PNG scores

High-quality PDF/SVG/PNG export uses MuseScore CLI. Start the API server with the binary path:

```bash
uv run canonize-web \
  --output-root ./runs \
  --musescore-bin /path/to/musescore
```

Then use the `Render PDF`, `Render SVG`, or `Render PNG` buttons in the `Exports` panel. If MuseScore is not configured, the render request returns a clear API error and the existing MIDI, MusicXML, report, results, and visualization downloads still work.

## Production build

Build the frontend:

```bash
cd web
pnpm build
```

Serve the built files from FastAPI:

```bash
uv run canonize-web --output-root ./runs --serve-frontend web/dist
```

The API routes remain under `/api`. Static frontend files are served from `web/dist`.

## Production notes

Run public browsing deployments with `--read-only` whenever users only need to inspect pre-generated runs. Read-only mode blocks uploads and score-render mutations while still serving existing `visualization.json`, artifacts, and downloads registered in `artifact_index.json`.

Place `--output-root` on durable storage with a clear retention policy. Generated runs, rendered scores, and `runs/_uploads/` can grow with every request; prune old run directories and upload staging directories on a schedule that matches your demo or deployment policy. Set disk quota alerts outside Kithairon before exposing a long-lived service.

Keep write endpoints private unless the deployment has an authentication or isolation plan. Upload and render routes accept user-provided files and can trigger CPU, memory, disk, and optional MuseScore work, so public demos should either run read-only or sit behind authentication, request-rate limits, and per-instance isolation.

Set body-size and rate limits in the reverse proxy. Match the proxy request-body limit to the API upload limit, which defaults to 10 MiB, and reject oversized requests before they reach the Python process. Use conservative worker and concurrency settings for small hosts because MusicXML parsing, generation, solver fallback, and MuseScore rendering can all be CPU-bound.

Configure CORS narrowly. Only pass `--cors-origin` for trusted frontend origins, and avoid wildcard origins on deployments that expose upload or render routes.

## Troubleshooting

If upload fails, check that the file extension is supported and the file is under the server upload limit.

If score rendering fails in the browser, the piano-roll, inspector, playback, and artifact downloads remain available.

If PDF/SVG/PNG rendering fails, check the `--musescore-bin` path and confirm the binary can be run from the shell.
