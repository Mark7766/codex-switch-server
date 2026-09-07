from __future__ import annotations

import base64
import json
import logging
import re
import time
from pathlib import Path

import markdown
from markupsafe import Markup

from src.config import settings
from src.utils.http import HttpClient
from src.utils.storage import LocalStorage

logger = logging.getLogger(__name__)

# Tools whose doc pages render a changelog, keyed by tool slug.
REPO_MAP = {
    "codex-switch": "Mark7766/codex-switch",
    "ai-working-ok": "Mark7766/ai-working-ok",
    "ai-coding-ok": "Mark7766/ai-coding-ok",
}

CACHE_DIR = "tool-changelog"

# Keep-a-Changelog version header: `## [v1.2.3] - 2026-09-06` (date optional).
_HEADER_RE = re.compile(r"^##\s+\[(?P<ver>[^\]]+)\]\s*[-–—]?\s*(?P<date>\d{4}-\d{2}-\d{2})?")

# Module-level Markdown instance is stateful: reset() before each convert.
_md = markdown.Markdown(extensions=["tables", "fenced_code", "sane_lists"])

# In-memory cache: {tool: (checked_at_epoch, entries)}
_cache: dict[str, tuple[float, list[dict]]] = {}


def repo_for(tool: str) -> str:
    """Return the GitHub 'owner/repo' for a tool slug (safe fallback to codex-switch)."""
    return REPO_MAP.get(tool, REPO_MAP["codex-switch"])


class ToolChangelogService:
    """Fetch and render a tool repo's CHANGELOG.md for the portal doc pages.

    Caching mirrors AiWorkingOkReleaseService: in-memory TTL + on-disk JSON,
    falling back to the last-known-good copy when GitHub is unreachable. Content
    is single-sourced in each tool repo, so a new tool release appears here
    automatically once the repo's CHANGELOG.md is updated.
    """

    def __init__(self, http: HttpClient | None = None, storage: LocalStorage | None = None):
        # Short timeout / single retry so a GitHub outage never stalls a whole page.
        self._http = http or HttpClient(timeout=8, max_retries=1)
        self._storage = storage or LocalStorage()

    async def get_changelog(self, tool: str) -> list[dict]:
        """Return newest-first entries [{version, date, html, is_first}, ...].

        Order: fresh in-memory -> fresh disk -> GitHub (writes cache) -> stale
        last-known-good -> []. Never raises: the caller renders an empty state.
        """
        ttl = settings.tool_changelog_cache_ttl
        now = time.time()

        mem = _cache.get(tool)
        if mem and now - mem[0] < ttl:
            return mem[1]

        disk = await self._load_disk(tool)
        if disk and now - disk[0] < ttl:
            _cache[tool] = disk
            return disk[1]

        fallback = disk or mem  # stale copy is better than nothing
        try:
            raw = await self._fetch_from_github(tool)
            entries = self.parse_changelog(raw)
        except Exception:
            logger.warning("Tool changelog fetch failed for %s", tool, exc_info=True)
            return fallback[1] if fallback else []

        _cache[tool] = (now, entries)
        try:
            await self._save_disk(tool, entries)
        except Exception:
            logger.warning("Tool changelog disk cache write failed for %s", tool, exc_info=True)
        return entries

    # ── GitHub ──────────────────────────────────────────────

    async def _fetch_from_github(self, tool: str) -> str:
        """Fetch and decode the repo's CHANGELOG.md via the contents API."""
        full_repo = repo_for(tool)
        url = f"https://api.github.com/repos/{full_repo}/contents/CHANGELOG.md"
        headers = {"Accept": "application/vnd.github+json"}
        if settings.github_token:
            headers["Authorization"] = f"Bearer {settings.github_token}"
        data = await self._http.get_json(url, headers=headers)
        encoded = data.get("content", "")
        return base64.b64decode(encoded).decode("utf-8", errors="replace")

    # ── Parsing & rendering ─────────────────────────────────

    @staticmethod
    def parse_changelog(raw: str) -> list[dict]:
        """Split CHANGELOG.md into per-version entries with pre-rendered HTML.

        Only lines under a ``## [version]`` header are kept (the leading h1 and
        preamble are dropped). ``[Unreleased]`` sections are skipped. The first
        kept (newest) entry gets ``is_first=True``.
        """
        entries: list[dict] = []
        ver: str | None = None
        date = ""
        body: list[str] = []

        def flush() -> None:
            nonlocal ver
            if ver is None:
                return
            if ver.lower() != "unreleased":
                text = "\n".join(body).strip()
                if text:
                    _md.reset()  # clear block-parser state before each convert
                    html = Markup(_md.convert(text))
                else:
                    html = Markup("")
                entries.append({"version": ver, "date": date, "html": html})
            ver = None

        for line in raw.splitlines():
            match = _HEADER_RE.match(line)
            if match:
                flush()
                ver = match.group("ver").strip()
                date = (match.group("date") or "").strip()
                body = []
            elif ver is not None:
                body.append(line)
        flush()

        for idx, entry in enumerate(entries):
            entry["is_first"] = idx == 0
        return entries

    # ── Disk cache helpers ──────────────────────────────────

    def _disk_key(self, tool: str) -> str:
        return f"{CACHE_DIR}/{tool}.json"

    async def _load_disk(self, tool: str) -> tuple[float, list[dict]] | None:
        path = await self._storage.get_path(self._disk_key(tool))
        if not path:
            return None
        try:
            data = json.loads(path.read_text())
            entries = [{**e, "html": Markup(e["html"]), "is_first": i == 0} for i, e in enumerate(data["entries"])]
            return float(data["checked_at"]), entries
        except Exception:
            return None

    async def _save_disk(self, tool: str, entries: list[dict]) -> None:
        payload = {
            "checked_at": time.time(),
            "entries": [{k: (str(v) if k == "html" else v) for k, v in e.items()} for e in entries],
        }
        tmp = Path(f"/tmp/tool-changelog-{tool}.json")
        tmp.write_text(json.dumps(payload, ensure_ascii=False))
        try:
            await self._storage.put(tmp, self._disk_key(tool))
        finally:
            tmp.unlink(missing_ok=True)
