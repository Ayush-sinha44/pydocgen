import re
from abc import ABC, abstractmethod

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
    @abstractmethod
    def generate_docstring(self, function_code: str) -> str:
        """Generate a docstring for the given function code."""
        pass

    @staticmethod
    def clean_output(text: str) -> str:
        """Clean the LLM output by removing thinking tags and markdown code blocks."""
        text = re.sub(r'<(thinking|thought)>.*?</\1>', '', text, flags=re.DOTALL)
        text = text.replace("```python", "").replace("```", "")
        return text.strip()


class OllamaClient(LLMClient):
    def __init__(self, model: str, url: str):
        self.model = model
        self.url = url

    def generate_docstring(self, function_code: str) -> str:
        response = requests.post(
            f"{self.url}/api/chat",
            json={
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": function_code
                    }
                ],
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 250
                }
            },
            timeout=90,
        )

        response.raise_for_status()

        cleaned = self.clean_output(response.json()["message"]["content"])

        cleaned = cleaned.removeprefix('"""')
        cleaned = cleaned.removesuffix('"""')

        return cleaned.strip()


class OpenAIClient(LLMClient):
    def __init__(self, model: str, api_key: str, base_url: str = None):
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "The 'openai' library is required to use the OpenAI provider. "
                "Install it with: pip install 'pydocgen[openai]'"
            )
        
        # Initialize the OpenAI client
        # If api_key is None, it defaults to checking the OPENAI_API_KEY env var
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def generate_docstring(self, function_code: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": function_code
                }
            ],
            temperature=0.1,
            max_tokens=250,
        )

        content = response.choices[0].message.content
        cleaned = self.clean_output(content)

        cleaned = cleaned.removeprefix('"""')
        cleaned = cleaned.removesuffix('"""')

        return cleaned.strip()


class GroqClient(LLMClient):
    def __init__(self, model: str, api_key: str):
        try:
            from groq import Groq
        except ImportError:
            raise ImportError(
                "The 'groq' library is required to use the Groq provider. "
                "Install it with: pip install 'pydocgen[groq]'"
            )
        
        # Initialize the Groq client
        # If api_key is None, it defaults to checking the GROQ_API_KEY env var
        self.client = Groq(api_key=api_key)
        self.model = model

    def generate_docstring(self, function_code: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": function_code
                }
            ],
            temperature=0.1,
            max_tokens=250,
        )

        content = response.choices[0].message.content
        cleaned = self.clean_output(content)

        cleaned = cleaned.removeprefix('"""')
        cleaned = cleaned.removesuffix('"""')

        return cleaned.strip()
