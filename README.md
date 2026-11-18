# EVA Video Demos

This repository contains a standalone static video showcase, with four
real-world demos (bottle placement, three-cup task, box transport, chair pushing)
and two simulation demos (monitor and recovery). Research text, results tables,
author information, paper/code links, and citations are omitted from the page.

## Local preview

```sh
python3 -m http.server 8000 --bind 0.0.0.0
```

Open http://localhost:8000. No build step or runtime framework is required.

## Videos

Real-world demos share a player with thumbnail selection. Simulation videos have
individual players and preserve their full frame. Starting a video pauses any
other playing video. All videos load on demand and retain their source edits,
embedded timestamps, and playback speed labels.

Original media and research source materials are excluded from this repository.
Lucide 0.468.0 supplies icons; see `assets/LUCIDE-LICENSE`.

## Configuration and deployment

Only `canonicalUrl` in `site.config.js` is used by this page. Other release fields
are retained for the full research page but are not displayed here.

All asset paths support project subpaths. The existing GitHub Pages workflow
publishes on pushes to `main` or manual dispatch once GitHub Pages is configured
to use GitHub Actions.

## Browser verification

```sh
python3 -m pip install selenium
python3 scripts/check_page.py --url http://127.0.0.1:8000
```

Requires Firefox and geckodriver. Checks responsive layout, navigation, all six
videos, asset URLs, project subpaths, canonical configuration, and JavaScript
errors. Screenshots are saved to `test-results/`.
