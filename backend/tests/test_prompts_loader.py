"""Tests for prompts.loader: PromptLoader + LoadedPrompt."""

from pathlib import Path

import pytest

from adjents.prompts.loader import LoadedPrompt, PromptLoader

PROMPTS_DIR = Path(__file__).parent.parent / "adjents" / "prompts"


def test_get_existing_prompt_returns_loaded_prompt() -> None:
    loader = PromptLoader(PROMPTS_DIR)
    prompt = loader.get("generator/interview")
    assert isinstance(prompt, LoadedPrompt)
    assert isinstance(prompt.content, str)


def test_frontmatter_types_parsed_correctly() -> None:
    loader = PromptLoader(PROMPTS_DIR)
    prompt = loader.get("generator/interview")
    assert prompt.frontmatter["version"] == 1
    assert isinstance(prompt.frontmatter["model_hint"], str)
    assert "claude" in prompt.frontmatter["model_hint"]


def test_frontmatter_description_is_string() -> None:
    loader = PromptLoader(PROMPTS_DIR)
    prompt = loader.get("generator/interview")
    assert isinstance(prompt.frontmatter["description"], str)
    assert len(prompt.frontmatter["description"]) > 0


def test_get_nonexistent_prompt_raises_file_not_found() -> None:
    loader = PromptLoader(PROMPTS_DIR)
    with pytest.raises(FileNotFoundError):
        loader.get("nonexistent/prompt")


def test_load_all_caches_all_prompts() -> None:
    loader = PromptLoader(PROMPTS_DIR)
    loader.load_all()
    prompt = loader.get("generator/interview")
    assert prompt is not None


def test_load_all_caches_multiple_prompts() -> None:
    loader = PromptLoader(PROMPTS_DIR)
    loader.load_all()
    count = sum(1 for _ in PROMPTS_DIR.rglob("*.md"))
    assert count >= 3


def test_render_substitutes_variables() -> None:
    prompt = LoadedPrompt(
        frontmatter={},
        content="Hello {name}, your domain is {domain}.",
    )
    result = prompt.render(name="Alex", domain="Finance")
    assert result == "Hello Alex, your domain is Finance."


def test_render_no_variables_returns_content_unchanged() -> None:
    prompt = LoadedPrompt(frontmatter={}, content="No placeholders here.")
    assert prompt.render() == "No placeholders here."


def test_get_caches_result_on_second_call() -> None:
    loader = PromptLoader(PROMPTS_DIR)
    p1 = loader.get("generator/interview")
    p2 = loader.get("generator/interview")
    assert p1 is p2
