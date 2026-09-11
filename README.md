# Elliptic-curve resource teaching site

Source and built pages for the IonQ elliptic-curve discrete-logarithm teaching notes.

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

Imported from the published Sites version 10, source commit `3e998ec43e19f5e23ab1a38d0b382f30722c3d83`. This repository is a snapshot; automatic deployment is not configured.

The notes include attributed figures from the source paper and vendored KaTeX. Original authors retain their respective rights; see source citations and bundled license files.
