"""
Service abstraction around the OpenAI API for blog generation.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI

from ..utils import normalise_whitespace


load_dotenv()


@dataclass(slots=True)
class AIResponse:
    """Structured response returned by the AI service."""

    content: str
    model: str


class AIService:
    """
    Thin wrapper over OpenAI's Responses API that generates long-form blog content.
    """

    def __init__(self, *, model: str | None = None) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is missing. Set it in your environment before running the app."
            )

        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self._client = OpenAI(api_key=api_key)

    async def generate_blog(self, title: str, tone: Optional[str] = None) -> AIResponse:
        """
        Generate a detailed, SEO-friendly blog post for the provided title.

        Args:
            title: Topic or heading supplied by the user.
            tone: Optional tone modifier (e.g. Formal, Conversational).

        Returns:
            An :class:`AIResponse` containing the generated text and metadata.
        """

        prompt = self._build_prompt(title=title, tone=tone)
        response = await asyncio.to_thread(self._invoke_model, prompt)
        content = normalise_whitespace(response)

        return AIResponse(content=content, model=self.model)

    def _invoke_model(self, prompt: str) -> str:
        response = self._client.responses.create(
            model=self.model,
            input=prompt,
        )

        content = getattr(response, "output_text", None)
        if content:
            return content

        if response.output:
            return response.output[0].content[0].text

        raise RuntimeError("OpenAI returned an empty response.")

    @staticmethod
    def _build_prompt(*, title: str, tone: Optional[str]) -> str:
        tone_clause = f"Write in a {tone.lower()} tone." if tone else ""
        return (
            "You are an expert marketing copywriter and SEO specialist.\n"
            f"{tone_clause}\n"
            "Generate a comprehensive blog article that is 600-800 words long.\n"
            "Include:\n"
            "- Captivating introduction\n"
            "- Multiple sections with h2/h3 headings\n"
            "- Bulleted lists where helpful\n"
            "- Actionable insights and examples\n"
            "- Conclusion with a call to action\n\n"
            f"Topic: {title.strip()}\n\n"
            "Return plain text that is readable as Markdown."
        )


