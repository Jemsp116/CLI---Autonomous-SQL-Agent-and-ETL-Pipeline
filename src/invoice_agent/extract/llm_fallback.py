from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from invoice_agent.agent.prompts import FULL_INVOICE_EXTRACTION_PROMPT
from invoice_agent.config import get_settings


_CACHE: dict[str, dict] = {}


@dataclass
class LlmExtractionResult:
    header: dict
    line_items: list[dict]
    summary: dict
    used_llm: bool


def _create_extraction_llm():
    settings = get_settings()
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=settings.extraction_model,
        openai_api_key=settings.openrouter_api_key,
        openai_api_base=settings.openrouter_api_base,
        temperature=0,
        model_kwargs={"response_format": {"type": "json_object"}},
    )


def extract_full_invoice_llm(pdf_path: str | Path, page_text: str) -> LlmExtractionResult:
    key = str(pdf_path)
    if key in _CACHE:
        cached = _CACHE[key]
        return LlmExtractionResult(**cached, used_llm=True)

    llm = _create_extraction_llm()
    prompt = FULL_INVOICE_EXTRACTION_PROMPT.format(invoice_text=page_text)
    response = llm.invoke(prompt)
    payload = json.loads(response.content)

    result = {
        "header": payload.get("header", {}),
        "line_items": payload.get("line_items", []),
        "summary": payload.get("summary", {}),
    }
    _CACHE[key] = result
    return LlmExtractionResult(**result, used_llm=True)


def clear_cache() -> None:
    _CACHE.clear()