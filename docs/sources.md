# Documentation sources

Sources were retrieved on 2026-10-15. They document current or stated product
behavior, not necessarily the 1.007 format found in the reference sample.

- XenoDream X 1.302 help PDF:
  `https://xenodream.com/downloads/XDX1302Help.pdf`. The retrieved file was
  8,494,018 bytes with SHA-256
  `b3af7fa64b46cc6b08d9a31bf51c130c9e305bda99df49aa9d1cb1a0cd6678d8`.
  Page 36 states that XenoDream X parameter files are text files with the
  `.xxp` extension. The PDF itself is not redistributed in this repository.
- XenoDream X Types of Objects:
  `https://www.xenodream.com/xdxobjectsui.htm`. Retrieved 2026-10-15. It
  documents named holon categories and current metamorph capacity, but no
  numeric `.xxp` type-code mapping.
- XenoDream downloads:
  `https://xenodream.com/downloads.htm`. Retrieved 2026-10-15. It identifies
  the downloadable help document as version 1.302.

The local PDF text search used `pypdf` because Poppler was unavailable. Search
results guided the page lookup but do not prove that unrelated terms are absent
from the manual.

