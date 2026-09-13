# Elliptic-curve resource teaching site

Source and built pages for the IonQ elliptic-curve discrete-logarithm teaching notes.

## Executable reproduction

The [reconstruction code and report](reconstruction/schrottenloher-ionq/RECONSTRUCTION.md) are merged into this repository. Read the [talk-style reproduction lesson](https://projects.yifanfrankzhang.com/ionq-ecdlp/lesson/reproduction/) for the logical gate counts, verification, and limitations. This reconstructs arithmetic circuits, not the full physical resource estimate.

## Build

Requires Python 3 and Node.js. KaTeX and its fonts are included.

```sh
cd website
python3 build.py
python3 scripts/audit_site.py dist
```

## Preview

```sh
python3 -m http.server 8000 --directory website/dist
```

Open http://localhost:8000. For static hosting, publish `website/dist`.

Canonical lesson content is in `website/content/*.json`; diagrams and assets are included. See `website/README.md` for the source layout and checks.

Imported from the published Sites version 10, source commit `3e998ec43e19f5e23ab1a38d0b382f30722c3d83`. The public revision is hosted at https://projects.yifanfrankzhang.com/ionq-ecdlp/ through the scoped Cloudflare Worker in `wrangler.jsonc`. Deployment is manual.

The notes include attributed figures from the source paper and vendored KaTeX. Original authors retain their respective rights; see source citations and bundled license files.

## Public deployment

```sh
SITE_BASE_PATH=/ionq-ecdlp python3 website/build.py
SITE_BASE_PATH=/ionq-ecdlp python3 website/scripts/audit_site.py website/dist
wrangler deploy
```

See `website/PUBLIC-REVISION.md` and `website/data/blog-revision.json` for the current audit and section-level edits.
