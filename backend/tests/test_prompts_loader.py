"""Tests for prompts.loader: PromptLoader, LoadedPrompt and the frontmatter parser.

Every case runs on files written to `tmp_path`, so no test depends on the content of
the real prompts, except the one checking that they all parse.
"""

from pathlib import Path

import pytest

from adjents.prompts.loader import LoadedPrompt, PromptLoader

PROMPTS_DIR = Path(__file__).parent.parent / "adjents" / "prompts"


def _loader_with(tmp_path: Path, text: str, key: str = "agent/intro") -> PromptLoader:
    """Write one prompt file byte for byte (no newline translation)."""
    path = tmp_path / f"{key}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))
    return PromptLoader(tmp_path)


# --- Frontmatter: accepted forms ---


def test_frontmatter_and_body_are_split(tmp_path: Path) -> None:
    loader = _loader_with(
        tmp_path,
        '---\nversion: 1\ndescription: "Intro: who I am"\nmodel_hint: local\n---\n'
        "\nYou are an agent.\n",
    )
    prompt = loader.get("agent/intro")
    assert prompt.frontmatter == {
        "version": 1,
        "description": "Intro: who I am",
        "model_hint": "local",
    }
    assert prompt.content == "You are an agent."


@pytest.mark.parametrize("value", ["-3", "1.5", "true", "²", "1e3"])
def test_only_ascii_digits_become_an_int(tmp_path: Path, value: str) -> None:
    """Anything else stays a string; `²` passes `str.isdigit()` but is not an int."""
    loader = _loader_with(tmp_path, f"---\nx: {value}\n---\nBody")
    assert loader.get("agent/intro").frontmatter == {"x": value}


def test_text_without_frontmatter_is_all_body(tmp_path: Path) -> None:
    loader = _loader_with(tmp_path, "You are an agent.\n")
    prompt = loader.get("agent/intro")
    assert prompt.frontmatter == {}
    assert prompt.content == "You are an agent.\n"


def test_empty_frontmatter_block_is_recognised(tmp_path: Path) -> None:
    prompt = _loader_with(tmp_path, "---\n---\nBody").get("agent/intro")
    assert (prompt.frontmatter, prompt.content) == ({}, "Body")


def test_blank_lines_inside_the_block_are_ignored(tmp_path: Path) -> None:
    prompt = _loader_with(tmp_path, "---\n\nversion: 1\n\n---\nBody").get("agent/intro")
    assert prompt.frontmatter == {"version": 1}


@pytest.mark.parametrize("newline", ["\r\n", "\r"], ids=["crlf", "cr"])
def test_line_endings_are_normalised(tmp_path: Path, newline: str) -> None:
    """Body included: the LLM gets the same text whatever the editor wrote."""
    text = newline.join(["---", "version: 1", "---", "Line 1", "Line 2", ""])
    prompt = _loader_with(tmp_path, text).get("agent/intro")
    assert (prompt.frontmatter, prompt.content) == ({"version": 1}, "Line 1\nLine 2")


def test_utf8_bom_is_dropped(tmp_path: Path) -> None:
    prompt = _loader_with(tmp_path, "﻿---\nversion: 1\n---\nBody").get("agent/intro")
    assert (prompt.frontmatter, prompt.content) == ({"version": 1}, "Body")


# --- Frontmatter: rejected forms ---


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("---\nversion: 1\n", "unterminated"),
        # An unterminated block would otherwise close on a `---` rule in the body.
        (
            "---\nversion: 1\nYou are the Generator.\n---\nRules: be brief.\n",
            "line 3",
        ),
        ("---\nversion:1\n---\nBody", "line 2"),
        ("---\nmy key: 1\n---\nBody", "line 2"),
        ("---\nx: 1\nx: 2\n---\nBody", "line 3"),
        ('---\nx: "\n---\nBody', "line 2"),
        ('---\nx: "abc\n---\nBody', "line 2"),
    ],
    ids=[
        "unterminated",
        "closed-by-a-rule",
        "no-space-after-colon",
        "key-not-an-identifier",
        "duplicate-key",
        "lone-quote",
        "unbalanced-quote",
    ],
)
def test_malformed_frontmatter_raises(tmp_path: Path, text: str, reason: str) -> None:
    """The prompt would otherwise reach the LLM with its frontmatter, or lose part of
    its body, silently."""
    loader = _loader_with(tmp_path, text)
    with pytest.raises(ValueError, match=reason) as exc_info:
        loader.get("agent/intro")
    assert "intro.md" in str(exc_info.value)


def test_error_message_does_not_quote_the_line(tmp_path: Path) -> None:
    loader = _loader_with(tmp_path, "---\nversion: 1\nsecret business text\n---\n")
    with pytest.raises(ValueError) as exc_info:
        loader.get("agent/intro")
    assert "secret business text" not in str(exc_info.value)


# --- PromptLoader ---


def test_get_returns_a_loaded_prompt(tmp_path: Path) -> None:
    prompt = _loader_with(tmp_path, "Body").get("agent/intro")
    assert prompt == LoadedPrompt(frontmatter={}, content="Body")


def test_get_missing_prompt_raises_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        PromptLoader(tmp_path).get("agent/missing")


def test_get_reads_the_file_once(tmp_path: Path) -> None:
    loader = _loader_with(tmp_path, "First")
    first = loader.get("agent/intro")
    (tmp_path / "agent" / "intro.md").write_text("Second", encoding="utf-8")
    assert loader.get("agent/intro") is first
    assert first.content == "First"


def test_load_all_caches_every_file_under_posix_keys(tmp_path: Path) -> None:
    """Keys use `/` whatever the OS, as `get()` callers write them."""
    loader = _loader_with(tmp_path, "Intro", key="agent/intro")
    _loader_with(tmp_path, "Interview", key="generator/interview")
    loader.load_all()
    for path in tmp_path.rglob("*.md"):
        path.unlink()
    assert loader.get("agent/intro").content == "Intro"
    assert loader.get("generator/interview").content == "Interview"


def test_load_all_replaces_cached_prompts(tmp_path: Path) -> None:
    loader = _loader_with(tmp_path, "First")
    loader.get("agent/intro")
    (tmp_path / "agent" / "intro.md").write_text("Second", encoding="utf-8")
    loader.load_all()
    assert loader.get("agent/intro").content == "Second"


@pytest.mark.parametrize("key", ["../outside", "agent/../../outside"])
def test_get_rejects_a_key_outside_the_directory(tmp_path: Path, key: str) -> None:
    (tmp_path / "outside.md").write_text("Outside", encoding="utf-8")
    prompts_dir = tmp_path / "prompts"
    (prompts_dir / "agent").mkdir(parents=True)
    with pytest.raises(ValueError, match="outside"):
        PromptLoader(prompts_dir).get(key)


def test_get_rejects_an_absolute_key(tmp_path: Path) -> None:
    (tmp_path / "outside.md").write_text("Outside", encoding="utf-8")
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    with pytest.raises(ValueError, match="outside"):
        PromptLoader(prompts_dir).get(str(tmp_path / "outside"))


# --- The real prompts ---


def test_every_real_prompt_parses() -> None:
    """The strict parser accepts every prompt shipped in `adjents/prompts/`."""
    loader = PromptLoader(PROMPTS_DIR)
    loader.load_all()
    keys = [
        path.relative_to(PROMPTS_DIR).with_suffix("").as_posix()
        for path in PROMPTS_DIR.rglob("*.md")
    ]
    assert len(keys) >= 5
    for key in keys:
        prompt = loader.get(key)
        assert isinstance(prompt.frontmatter["version"], int), key
        assert prompt.content, key
