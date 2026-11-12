"""Prompt loader — reads and caches the `.md` prompt files (frontmatter + body).

Prompts never live in Python source: each one is a Markdown file under
`adjents/prompts/<agent_type>/<purpose>.md` (ARCHITECTURE §9), so it can be edited
and reviewed without touching code. A file may start with a frontmatter block
between two `---` lines (`version`, `description`, `model_hint`…), followed by the
prompt body. The frontmatter is parsed by hand, not by a YAML library: only flat
`key: value` lines are understood, and anything else in the block is an error, so a
malformed file fails at load time instead of reaching the LLM with its frontmatter.

Place in the flow: the caller builds one `PromptLoader` on the prompts directory
(today the smoke scripts) and injects it into the orchestrators. They call
`get(key).content` to obtain a system prompt — keys `generator/interview`,
`generator/extract_business_context`, `generator/org_generation`, `agent/intro`,
`agent/extract_agent_adjustments` — and the interview also reads the
`kickoff_message` frontmatter key. Nothing reads `model_hint`: the model is chosen
by `LLMRouter`. `load_all()` is called by no production code. Prompts are fixed
texts: there is no templating (agent context reaches the LLM in a message).

Entry points: `PromptLoader`, `LoadedPrompt`.

Related: ARCHITECTURE §9 (prompt management). No ADR.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_DELIMITER = "---"
_KEY = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
# `[0-9]`, not `str.isdigit()`: `isdigit()` accepts characters such as `²` that
# `int()` rejects.
_INT = re.compile(r"[0-9]+")


def _parse_value(raw: str, where: str) -> str | int:
    if raw.startswith('"'):
        if len(raw) < 2 or not raw.endswith('"'):
            raise ValueError(f"{where}: unbalanced double quote")
        return raw[1:-1]
    if _INT.fullmatch(raw):
        return int(raw)
    return raw


def _parse_frontmatter(text: str, source: str) -> tuple[dict[str, str | int], str]:
    """Split a prompt file into its frontmatter and its body.

    The text has a frontmatter block when its first line is exactly `---`; the
    block ends at the next line that is exactly `---`, and may be empty. Without
    that first line, the result is `({}, text)`, the whole text being the body.

    Inside the block, blank lines are skipped and every other line must be
    `key: value`: a key made of letters, digits and underscores (not starting with
    a digit), then `": "`, then the value, stripped. A key may appear once. Values
    are converted as follows:

    - wrapped in double quotes → the string between them (an unbalanced quote is
      an error);
    - ASCII digits only → `int` (so `-3`, `1.5` and `²` stay strings);
    - anything else → the raw string (`true` stays the string `"true"`).

    Args:
        text: Full content of the prompt file, with `\\n` line endings.
        source: Name of the file, for error messages.

    Returns:
        A `(frontmatter, body)` pair. The body is stripped of leading and trailing
        whitespace when a frontmatter block was found.

    Raises:
        ValueError: The block is not closed, or one of its lines is not a valid
            `key: value` line. The message gives the file and the line number,
            never the line itself.
    """
    lines = text.split("\n")
    if lines[0] != _DELIMITER:
        return {}, text
    try:
        end = lines.index(_DELIMITER, 1)
    except ValueError:
        raise ValueError(
            f"{source}: unterminated frontmatter (no closing '---' line)"
        ) from None
    frontmatter: dict[str, str | int] = {}
    for number, line in enumerate(lines[1:end], start=2):
        if not line.strip():
            continue
        where = f"{source}, line {number}"
        key, separator, raw = line.partition(": ")
        if not separator or not _KEY.fullmatch(key):
            raise ValueError(f"{where}: expected a 'key: value' line")
        if key in frontmatter:
            raise ValueError(f"{where}: duplicate key {key!r}")
        frontmatter[key] = _parse_value(raw.strip(), where)
    return frontmatter, "\n".join(lines[end + 1 :]).strip()


@dataclass
class LoadedPrompt:
    """A prompt file once loaded: its frontmatter and its body.

    Attributes:
        frontmatter: Parsed frontmatter keys; empty when the file has none.
        content: The prompt body, used as is as a system prompt.
    """

    frontmatter: dict[str, str | int]
    content: str


class PromptLoader:
    """Loads prompt files from one directory and caches them by key.

    A key is the file path relative to the directory, with `/` separators and
    without the `.md` suffix, e.g. `"generator/interview"`. `get()` reads a file
    only on its first access; a file changed on disk afterwards is not reloaded,
    unless `load_all()` is called again. Files are read as UTF-8, a leading byte
    order mark dropped; `read_text()` turns `\\r\\n` and `\\r` line endings into
    `\\n`.

    Args:
        prompts_dir: Root directory of the prompt files.
    """

    def __init__(self, prompts_dir: Path) -> None:
        self._dir = prompts_dir
        self._cache: dict[str, LoadedPrompt] = {}

    def load_all(self) -> None:
        """Load every `.md` file under the directory, recursively, into the cache.

        Files already cached are read again and replaced.

        Raises:
            ValueError: A file has a malformed frontmatter.
        """
        for path in self._dir.rglob("*.md"):
            key = path.relative_to(self._dir).with_suffix("").as_posix()
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
            ValueError: The key resolves outside the directory (`..`, absolute
                path), or the file has a malformed frontmatter.
        """
        if key not in self._cache:
            path = (self._dir / f"{key}.md").resolve()
            if not path.is_relative_to(self._dir.resolve()):
                raise ValueError(f"Prompt key resolves outside {self._dir}: {key!r}")
            if not path.exists():
                raise FileNotFoundError(f"Prompt not found: {path}")
            self._cache[key] = self._load(path)
        return self._cache[key]

    def _load(self, path: Path) -> LoadedPrompt:
        """Read one prompt file and split it into frontmatter and body."""
        text = path.read_text(encoding="utf-8-sig")
        frontmatter, content = _parse_frontmatter(text, source=str(path))
        return LoadedPrompt(frontmatter=frontmatter, content=content)
