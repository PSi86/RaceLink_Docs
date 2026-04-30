"""
MkDocs hook: rewrite relative source-code references to GitHub URLs.

Why this hook exists
--------------------

The narrative docs in this repo intentionally cross-reference source
files that live in the sibling *component* repositories
(``RaceLink_Host``, ``RaceLink_Gateway``, ``RaceLink_WLED``,
``RaceLink_RH-plugin``). The relative paths work when the markdown
is read **inside** the relevant component repo, where the source
tree is one level up; but when MkDocs builds this docs repo it has
no idea those targets exist, and warns on every one of them.

Rather than weaken ``validation.links.not_found`` globally — which
would also silence warnings on truly broken internal cross-links —
this hook rewrites the relative source refs to absolute GitHub
URLs at build time. The source markdown stays component-repo
portable; the published site gets working, clickable links.

Adding a new mapping
--------------------

Add a tuple to ``RULES`` below. Earlier rules win on overlap
(though we deliberately keep the patterns non-overlapping). The
``file_glob`` is matched against ``page.file.src_uri`` (always
forward-slash, relative to ``docs/``).

If a component repo is renamed or the default branch changes,
update only the four ``HOST`` / ``GATEWAY`` / ``WLED`` / ``RH``
constants; the rules will follow.
"""
from __future__ import annotations

import fnmatch


# ---- Repo blob-URL prefixes (single source of truth) ----------------

HOST    = "https://github.com/PSi86/RaceLink_Host/blob/main"
GATEWAY = "https://github.com/PSi86/RaceLink_Gateway/blob/main"
WLED    = "https://github.com/PSi86/RaceLink_WLED/blob/main"
RH      = "https://github.com/PSi86/RaceLink_RH-plugin/blob/main"
DOCS    = "https://github.com/PSi86/RaceLink_Docs/blob/main"


# ---- Rules ----------------------------------------------------------
#
# Each tuple: (file_glob, link_prefix, url_prefix)
#
#   file_glob   : fnmatch pattern against page.file.src_uri
#                 (e.g. "RaceLink_Host/*.md")
#   link_prefix : exact prefix that the markdown link target starts
#                 with after ``](`` (e.g. "../racelink/")
#   url_prefix  : replacement; the GitHub blob-URL prefix
#
# The hook replaces the literal string ``](<link_prefix>`` with
# ``](<url_prefix>`` — anchored by the closing ``](`` of a markdown
# link, so it only fires at link-target start, never inside text.

RULES = [
    # docs/RaceLink_Host/architecture.md uses bare paths from the
    # host repo root: "racelink/..." (no leading "../")
    ("RaceLink_Host/architecture.md", "racelink/",                    HOST + "/racelink/"),

    # docs/RaceLink_Host/*.md (operator-guide, developer-guide,
    # ui-conventions, standalone-install, webui-guide) used to live in
    # `host/docs/` and reference the repo root via "../"
    ("RaceLink_Host/*.md",            "../racelink/",                 HOST + "/racelink/"),
    ("RaceLink_Host/*.md",            "../tests/",                    HOST + "/tests/"),
    ("RaceLink_Host/*.md",            "../controller.py",             HOST + "/controller.py"),
    ("RaceLink_Host/*.md",            "../racelink_proto.h",          HOST + "/racelink_proto.h"),
    ("RaceLink_Host/*.md",            "../gen_racelink_proto_py.py",  HOST + "/gen_racelink_proto_py.py"),
    ("RaceLink_Host/*.md",            "../gen_wled_metadata.py",      HOST + "/gen_wled_metadata.py"),

    # PROTOCOL.md is now reference/wire-protocol.md and references
    # the gateway repo via its workstation-style path
    ("reference/wire-protocol.md",    "../racelink/",                 HOST + "/racelink/"),
    ("reference/wire-protocol.md",    "../tests/",                    HOST + "/tests/"),
    ("reference/wire-protocol.md",    "../racelink_proto.h",          HOST + "/racelink_proto.h"),
    ("reference/wire-protocol.md",    "../gen_racelink_proto_py.py",  HOST + "/gen_racelink_proto_py.py"),
    ("reference/wire-protocol.md",    "../../RaceLink_Gateway/",      GATEWAY + "/"),

    # RaceLink_Host/developer-guide.md references the WLED fork
    # via the workstation-style "WLED LoRa/WLED/" path
    ("RaceLink_Host/*.md",            "../../WLED%20LoRa/WLED/",      WLED + "/"),

    # docs/concepts/deterministic-effects.md (was wled/docs/) uses
    # "../../wled00/..." for the WLED tree
    ("concepts/deterministic-effects.md", "../../wled00/",            WLED + "/wled00/"),

    # docs/assets/screenshots/README.md uses "../../../scripts/..."
    ("assets/screenshots/*.md",       "../../../scripts/",            DOCS + "/scripts/"),
]


def on_page_markdown(markdown, *, page, config, files):
    """Rewrite relative source refs in this page to absolute GitHub URLs."""
    src = page.file.src_uri  # always forward-slash, relative to docs/
    for file_glob, link_prefix, url_prefix in RULES:
        if not fnmatch.fnmatch(src, file_glob):
            continue
        markdown = markdown.replace(
            "](" + link_prefix,
            "](" + url_prefix,
        )
    return markdown
