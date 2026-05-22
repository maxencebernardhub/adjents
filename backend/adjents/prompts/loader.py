"""Prompt loader — loads and caches .md files with YAML frontmatter."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text
    rest = text[4:]
    end = rest.find("\n---\n")
    if end == -1:
        return {}, text
    fm_lines = rest[:end].splitlines()
    content = rest[end + 5 :].strip()
    frontmatter: dict[str, Any] = {}
    for line in fm_lines:
        if ": " not in line:
            continue
        key, _, raw = line.partition(": ")
        value = raw.strip()
        if value.startswith('"') and value.endswith('"'):
            frontmatter[key.strip()] = value[1:-1]
        elif value.isdigit():
            frontmatter[key.strip()] = int(value)
        else:
            frontmatter[key.strip()] = value
    return frontmatter, content


@dataclass
class LoadedPrompt:
    frontmatter: dict[str, Any]
    content: str

    def render(self, **kwargs: str) -> str:
        return self.content.format_map(kwargs)


class PromptLoader:
    def __init__(self, prompts_dir: Path) -> None:
        self._dir = prompts_dir
        self._cache: dict[str, LoadedPrompt] = {}

    def load_all(self) -> None:
        for path in self._dir.rglob("*.md"):
            key = str(path.relative_to(self._dir).with_suffix(""))
            self._cache[key] = self._load(path)

    def get(self, key: str) -> LoadedPrompt:
        if key not in self._cache:
            path = self._dir / f"{key}.md"
            if not path.exists():
                raise FileNotFoundError(f"Prompt not found: {path}")
            self._cache[key] = self._load(path)
        return self._cache[key]

    def _load(self, path: Path) -> LoadedPrompt:
        text = path.read_text(encoding="utf-8")
        frontmatter, content = _parse_frontmatter(text)
        return LoadedPrompt(frontmatter=frontmatter, content=content)
