# Public blog revision — 11 September 2026

All 50 lessons retain their section anchors, source references, worked circuits, and derivations. Openings now explain each mechanism directly. The landing page follows the argument from Fourier sampling to arithmetic, scheduling, and hardware. Removed 290 repeated editorial purpose panels, preserving appended definitions. The conclusion collects limitations and distinguishes one attempt from expected repeated-attempt cost.

The section-by-section record is `data/blog-revision.json`. This is an exposition and consistency review, with headline quantities compared to the source paper and executable teaching examples checked. It does not reproduce the authors’ internal compiler, decoder simulations, or full hardware estimate.

The build now accepts `SITE_BASE_PATH=/ionq-ecdlp`, covering navigation, source figures, data downloads, and the runtime chart. HTML-sensitive comparisons are escaped before math rendering. The static audit accepts the same prefix. Runtime data-loading failure now displays an explicit fallback message.

Validation: 50 pages, 4,177 rendered math expressions, 75 explanatory SVGs; zero static link, anchor, math, or image-alt errors. Division replay, context examples, lookup/measurement cleanup, and all 49 Fourier-control settings pass. The imported context test expected seven diagrams, but the original repository contains six; removed the unrelated fixed-count assertion while preserving algebraic checks. The materialized copy builds and audits independently without symlinks.

In-app browser: all 50 pages checked at desktop and 390-pixel widths for rendered headings, math errors, page overflow, and footer presence. No page-wide overflow or KaTeX error appeared. Representative screenshots and interactive controls were also inspected. Source circuit drawings intentionally scroll within their own containers on small screens.
