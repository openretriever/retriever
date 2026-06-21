# Third-Party Notices

Retriever vendors a small set of JavaScript assets so generated IR visualization
HTML files can open offline. The runtime also references public CDN URLs for the
same libraries when appropriate.

## Cytoscape.js

- Local file: `src/retriever/ir/assets/cytoscape.min.js`
- Version used by CDN fallback: `3.26.0`
- Upstream project: https://js.cytoscape.org/
- License: MIT
- Copyright: Copyright (c) 2016-2023, The Cytoscape Consortium.

The bundled minified file includes the upstream MIT license notice.

## Dagre

- Local file: `src/retriever/ir/assets/dagre.min.js`
- Version used by CDN fallback: `0.8.5`
- Upstream project: https://github.com/dagrejs/dagre
- License: MIT
- Copyright: Copyright (c) 2012-2014 Chris Pettitt.

The bundled minified file includes the upstream MIT license notice.

## Graphlib

- Local file: embedded inside `src/retriever/ir/assets/dagre.min.js`
- Upstream project: https://github.com/dagrejs/graphlib
- License: BSD-style license
- Copyright: Copyright (c) 2014, Chris Pettitt.

The bundled Dagre artifact includes Graphlib and its redistribution notice.

## cytoscape-dagre

- Local file: `src/retriever/ir/assets/cytoscape-dagre.min.js`
- Version used by CDN fallback: `2.5.0`
- Upstream package: https://www.npmjs.com/package/cytoscape-dagre
- Source repository: https://github.com/cytoscape/cytoscape.js-dagre
- License: MIT

The local file was minified by jsDelivr from the upstream npm package. Keep this
notice with the vendored artifact because the minified file itself only contains
the jsDelivr minification header.
