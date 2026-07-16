"""LLM client implementations for generating docstrings via different providers."""

import re
from abc import ABC, abstractmethod
from typing import Optional

import requests

SYSTEM_PROMPT = """
You are a senior Python engineer.
Generate a Google-style docstring for this Python function. 
Follow this exact structure:
1. A one-line summary.
2. An 'Args:' section listing each parameter with its type and purpose.
3. A 'Returns:' section describing the return value and type.
4. A 'Raises:' section if the code explicitly raises an exception.

- Do not include sections with no content
- Never include "Raises: None"
- Avoid obvious descriptions

Return ONLY the docstring text, starting and ending with triple double-quotes (\"\"\").
"""


class LLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    def generate_docstring(self, function_code: str) -> str:
        """Generate a docstring for the given function code."""
        pass

    @staticmethod
    def clean_output(text: str) -> str:
        """Clean the LLM output by removing thinking tags and markdown code blocks."""
        text = re.sub(r"<(thinking|thought)>.*?</\1>", "", text, flags=re.DOTALL)
        text = text.replace("```python", "").replace("```", "")
        return text.strip()


class OllamaClient(LLMClient):
    """LLM client for locally running Ollama instances."""

    def __init__(self, model: str, url: str):
        """Initialize the Ollama client.

        Args:
            model (str): The Ollama model name to use.
            url (str): The base URL of the Ollama API.
        """
        self.model = model
        self.url = url

    def generate_docstring(self, function_code: str) -> str:
        """Generate a docstring using the local Ollama API.

        Args:
            function_code (str): The source code of the function.

        Returns:
            str: The generated docstring text.
        """
        response = requests.post(
            f"{self.url}/api/chat",
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": function_code},
                ],
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 250},
            },
            timeout=90,
        )

        response.raise_for_status()

        cleaned = self.clean_output(response.json()["message"]["content"])

        cleaned = cleaned.removeprefix('"""')
        cleaned = cleaned.removesuffix('"""')

        return cleaned.strip()


class OpenAIClient(LLMClient):
    """LLM client for the OpenAI API."""

    def __init__(self, model: str, api_key: str, base_url: Optional[str] = None):
        """Initialize the OpenAI client.

        Args:
            model (str): The OpenAI model name to use.
            api_key (str): The OpenAI API key. Falls back to OPENAI_API_KEY env var if None.
            base_url (Optional[str]): Custom API base URL. Defaults to OpenAI's standard endpoint.
        """
        try:
            from openai import OpenAI
        except ImportError as e:
            raise ImportError(
                "The 'openai' library is required to use the OpenAI provider. "
                "Install it with: pip install 'pydocgen[openai]'"
            ) from e

        # Initialize the OpenAI client
        # If api_key is None, it defaults to checking the OPENAI_API_KEY env var
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def generate_docstring(self, function_code: str) -> str:
        """Generate a docstring using the OpenAI API.

        Args:
            function_code (str): The source code of the function.

        Returns:
            str: The generated docstring text.
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": function_code},
            ],
            temperature=0.1,
            max_tokens=250,
            timeout=90,
        )

        content = response.choices[0].message.content
        cleaned = self.clean_output(content)

        cleaned = cleaned.removeprefix('"""')
        cleaned = cleaned.removesuffix('"""')

        return cleaned.strip()


class GroqClient(LLMClient):
    """LLM client for the Groq API."""

    def __init__(self, model: str, api_key: str, base_url: Optional[str] = None):
        """Initialize the Groq client.

        Args:
            model (str): The Groq model name to use.
            api_key (str): The Groq API key. Falls back to GROQ_API_KEY env var if None.
            base_url (Optional[str]): Custom API base URL. Defaults to Groq's standard endpoint.
        """
        try:
            from groq import Groq
        except ImportError as e:
            raise ImportError(
                "The 'groq' library is required to use the Groq provider. "
                "Install it with: pip install 'pydocgen[groq]'"
            ) from e

        # Initialize the Groq client
        # If api_key is None, it defaults to checking the GROQ_API_KEY env var
        self.client = Groq(api_key=api_key, base_url=base_url)
        self.model = model

    def generate_docstring(self, function_code: str) -> str:
        """Generate a docstring using the Groq API.

        Args:
            function_code (str): The source code of the function.

        Returns:
            str: The generated docstring text.
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": function_code},
            ],
            temperature=0.1,
            max_tokens=250,
            timeout=90,
        )

        content = response.choices[0].message.content
        cleaned = self.clean_output(content)

        cleaned = cleaned.removeprefix('"""')
        cleaned = cleaned.removesuffix('"""')

        return cleaned.strip()
