from __future__ import annotations

import os
import platform
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from invoice_agent.config import get_settings


ENV_PATH = Path(".env")
ENV_EXAMPLE_PATH = Path(".env.example")


@dataclass(frozen=True)
class ApiKeyResult:
    key_found: bool
    persisted: bool
    warning: str | None = None


def find_ghostscript() -> str | None:
    for executable in ("gswin64c", "gswin32c", "gs"):
        found = shutil.which(executable)
        if found:
            return found
    return None


def ghostscript_install_instructions() -> str:
    system = platform.system().lower()
    if system == "windows":
        return "Windows: Install from https://ghostscript.com/releases/gsdnld.html and restart your terminal."
    if system == "darwin":
        return "macOS: brew install ghostscript"
    return "Linux: sudo apt-get install ghostscript"


def is_plausible_openrouter_key(value: str) -> bool:
    key = value.strip()
    if len(key) < 20:
        return False
    if any(char.isspace() for char in key):
        return False
    return key.startswith(("sk-or-", "sk-"))


def ensure_openrouter_api_key(prompt_func: Callable[[str], str]) -> ApiKeyResult:
    settings = get_settings()
    existing_key = settings.openrouter_api_key
    if existing_key and is_plausible_openrouter_key(existing_key):
        return ApiKeyResult(key_found=True, persisted=True)

    prompt = (
        "No OpenRouter API key found.\n"
        "Get one free at https://openrouter.ai/keys (sign up -> Create Key)\n"
        "Paste your key here: "
    )

    key = prompt_func(prompt).strip()
    if not is_plausible_openrouter_key(key):
        raise ValueError("The OpenRouter API key entered does not look valid.")

    os.environ["OPENROUTER_API_KEY"] = key
    try:
        _write_key_to_env(key)
    except OSError:
        get_settings.cache_clear()
        return ApiKeyResult(
            key_found=True,
            persisted=False,
            warning="Could not write .env. The key will be used for this session only.",
        )

    get_settings.cache_clear()
    return ApiKeyResult(key_found=True, persisted=True)


def _write_key_to_env(key: str) -> None:
    if not ENV_PATH.exists() and ENV_EXAMPLE_PATH.exists():
        ENV_PATH.write_text(ENV_EXAMPLE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    elif not ENV_PATH.exists():
        ENV_PATH.write_text("", encoding="utf-8")

    lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    replaced = False
    updated_lines = []

    for line in lines:
        if line.startswith("OPENROUTER_API_KEY="):
            updated_lines.append(f"OPENROUTER_API_KEY={key}")
            replaced = True
        else:
            updated_lines.append(line)

    if not replaced:
        updated_lines.append(f"OPENROUTER_API_KEY={key}")

    ENV_PATH.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")
