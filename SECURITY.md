# Security Policy

## Supported versions

Kithairon is a public preview. Security fixes target the current `main` branch and the latest tagged release when a practical patch release is needed.

## Reporting a vulnerability

Do not open a public issue for vulnerabilities. Report suspected security problems through GitHub private vulnerability reporting if it is available for this repository, or email `gnuicecream@gmail.com` with:

- affected version or commit;
- reproduction steps;
- expected impact;
- whether the issue affects the CLI, upload API, render API, generated artifacts, or documentation site.

You should receive an acknowledgement within 7 days. If the report is valid, the fix will be developed privately when needed and disclosed after a patched commit or release is available.

## API deployment risk

The visualization API accepts MusicXML and MIDI uploads and can optionally invoke MuseScore for PDF/SVG/PNG rendering. Do not expose upload or render endpoints on a public network without authentication, request-size limits, rate limits, and an isolation plan. Public demo deployments should prefer `canonize-web --read-only` with pre-generated runs.
