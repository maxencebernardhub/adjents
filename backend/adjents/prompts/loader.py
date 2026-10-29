"""Prompt loader — reads and caches the `.md` prompt files (frontmatter + body).

Prompts never live in Python source: each one is a Markdown file under
`adjents/prompts/<agent_type>/<purpose>.md` (ARCHITECTURE §9), so it can be edited
and reviewed without touching code. A file may start with a frontmatter block
between two `---` lines (`version`, `description`, `model_hint`…), followed by the
prompt body. The frontmatter is parsed by hand, not by a YAML library: only flat
`key: value` lines are understood.

Place in the flow: the caller builds one `PromptLoader` on the prompts directory
(today the smoke scripts) and injects it into the orchestrators. They call
`get(key).content` to obtain a system prompt — keys `generator/interview`,
`generator/extract_business_context`, `generator/org_generation`, `agent/intro`,
`agent/extract_agent_adjustments` — and the interview also reads the
`kickoff_message` frontmatter key. Nothing reads `model_hint`: the model is chosen
by `LLMRouter`. `load_all()` and `LoadedPrompt.render()` are called by no
production code.

Entry points: `PromptLoader`, `LoadedPrompt`.

Related: ARCHITECTURE §9 (prompt management). No ADR.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Split a prompt file into its frontmatter and its body.

    The frontmatter is recognised only when the text starts with a `---\\n` line
    and contains a later `\\n---\\n` line; otherwise the result is `({}, text)`,
    the whole text being returned unchanged as the body.

    Inside the block, each line containing `": "` is split at its first `": "`
    into a key and a value, both stripped; other lines are skipped. Values are
    converted as follows:

    - wrapped in double quotes → the string between them;
    - `str.isdigit()` true → `int(value)` (so `-3` and `1.5` stay strings);
    - anything else → the raw string (`true` stays the string `"true"`).

    Args:
        text: Full content of the prompt file.

    Returns:
        A `(frontmatter, body)` pair. The body is stripped of leading and trailing
        whitespace when a frontmatter block was found.

    Raises:
        ValueError: A value that `str.isdigit()` accepts but `int()` rejects, such
            as a Unicode digit (`²`).
    """
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
    """A prompt file once loaded: its frontmatter and its body.

    Attributes:
        frontmatter: Parsed frontmatter keys; empty when the file has none.
        content: The prompt body, used as is as a system prompt.
    """

    frontmatter: dict[str, Any]
    content: str

    def render(self, **kwargs: str) -> str:
        """Return `content` with `{name}` placeholders replaced by `str.format_map`."""
        return self.content.format_map(kwargs)


class PromptLoader:
    """Loads prompt files from one directory and caches them by key.

    A key is the file path relative to the directory, without the `.md` suffix,
    e.g. `"generator/interview"`. `get()` reads a file (UTF-8) only on its first
    access; a file changed on disk afterwards is not reloaded, unless
    `load_all()` is called again.

    Args:
        prompts_dir: Root directory of the prompt files.
    """

    def __init__(self, prompts_dir: Path) -> None:
        self._dir = prompts_dir
        self._cache: dict[str, LoadedPrompt] = {}

    def load_all(self) -> None:
        """Load every `.md` file under the directory, recursively, into the cache.

        Files already cached are read again and replaced.
        """
        for path in self._dir.rglob("*.md"):
            key = str(path.relative_to(self._dir).with_suffix(""))
            self._cache[key] = self._load(path)

    def get(self, key: str) -> LoadedPrompt:
        """Return the prompt for `key`, reading its file on first access.

        Args:
            key: Prompt key, e.g. `"agent/intro"`.

        Returns:
            The cached `LoadedPrompt` — the same object on every call, until
            `load_all()` replaces it.

        Raises:
            FileNotFoundError: No `<key>.md` file exists in the directory.
        """
        if key not in self._cache:
            path = self._dir / f"{key}.md"
            if not path.exists():
                raise FileNotFoundError(f"Prompt not found: {path}")
            self._cache[key] = self._load(path)
        return self._cache[key]

    def _load(self, path: Path) -> LoadedPrompt:
        """Read one prompt file and split it into frontmatter and body."""
        text = path.read_text(encoding="utf-8")
        frontmatter, content = _parse_frontmatter(text)
        return LoadedPrompt(frontmatter=frontmatter, content=content)
