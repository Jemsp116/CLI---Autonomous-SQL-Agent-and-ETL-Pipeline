from __future__ import annotations

import textwrap
from collections.abc import Sequence

from rich.console import Group
from rich.padding import Padding
from rich.spinner import Spinner
from rich.text import Text


def _wrapped_line_count(content: str, width: int) -> int:
    usable_width = max(24, width - 6)
    total = 0
    paragraphs = content.splitlines() or [""]

    for paragraph in paragraphs:
        wrapped = textwrap.wrap(
            paragraph,
            width=usable_width,
            replace_whitespace=False,
            drop_whitespace=False,
        )
        total += len(wrapped) if wrapped else 1

    return total


def _message_height(content: str, width: int) -> int:
    return 1 + _wrapped_line_count(content, width) + 1


def _select_visible_messages(
    messages: Sequence[tuple[str, str]],
    width: int,
    max_height: int,
) -> list[tuple[str, str]]:
    if not messages:
        return []

    visible: list[tuple[str, str]] = []
    remaining = max_height

    for role, content in reversed(messages):
        height = _message_height(content, width)
        if visible and height > remaining:
            break
        if not visible and height > max_height:
            visible.append((role, content))
            break

        visible.append((role, content))
        remaining -= height

    visible.reverse()
    return visible


def _message_renderable(role: str, content: str):
    title = "User" if role == "user" else "Assistant"
    title_style = "bold cyan" if role == "user" else "bold green"
    body_style = "white" if role == "user" else "bright_white"
    body = Text(content, style=body_style, overflow="fold")

    return Group(
        Text(title, style=title_style),
        Padding(body, (0, 0, 1, 2)),
    )


def render_conversation(
    messages: Sequence[tuple[str, str]],
    width: int,
    max_height: int,
    *,
    thinking: bool = False,
    draft_assistant: str = "",
):
    visible_messages = list(messages)
    if thinking and not draft_assistant:
        visible_messages.append(("assistant", "__thinking__"))
    elif draft_assistant:
        visible_messages.append(("assistant", draft_assistant))

    visible_messages = _select_visible_messages(visible_messages, width, max_height)

    blocks = []
    for role, content in visible_messages:
        if role == "assistant" and content == "__thinking__":
            blocks.append(Text("Assistant", style="bold green"))
            blocks.append(Padding(Spinner("dots", text="Thinking..."), (0, 0, 1, 2)))
            continue
        blocks.append(_message_renderable(role, content))

    if not blocks:
        blocks.append(Text("No messages yet.", style="dim"))

    return Group(*blocks)