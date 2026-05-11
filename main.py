import ast
import argparse
from pathlib import Path
import re

import requests


EXCLUDED_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "node_modules",
    ".mypy_cache",
    ".pytest_cache",
}


class OllamaClient:
    def __init__(self, model: str, url: str):
        self.model = model
        self.url = url

    def generate_docstring(self, function_code: str) -> str:
        SYSTEM_PROMPT = f"""
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

    @staticmethod
    def clean_output(text: str) -> str:
        text = re.sub(r'<(thinking|thought)>.*?</\1>', '', text, flags=re.DOTALL)
        text = text.replace("```python", "").replace("```", "")
        return text.strip()


class DocstringAdder(ast.NodeTransformer):

    def __init__(
        self,
        llm_client: OllamaClient,
        overwrite_existing: bool = False,
        skip_private: bool = True,
    ):
        self.llm_client = llm_client
        self.overwrite_existing = overwrite_existing
        self.skip_private = skip_private

    def process_function(self, node):

        if self.skip_private and node.name.startswith("_"):
            return node

        if not self.overwrite_existing and ast.get_docstring(node):
            return node

        try:
            function_code = ast.unparse(node)

            print(f"Generating docstring for: {node.name}")

            docstring = self.llm_client.generate_docstring(function_code)

            node.body.insert(
                0,
                ast.Expr(value=ast.Constant(value=docstring))
            )

        except Exception as e:
            print(f"Failed on function '{node.name}': {e}")

        return node

    def visit_FunctionDef(self, node):
        self.generic_visit(node)
        return self.process_function(node)

    def visit_AsyncFunctionDef(self, node):
        self.generic_visit(node)
        return self.process_function(node)


def process_file(
    filepath: Path,
    transformer: DocstringAdder,
):
    try:
        source = filepath.read_text(encoding="utf-8")

        tree = ast.parse(source)

        updated_tree = transformer.visit(tree)

        filepath.write_text(
            ast.unparse(updated_tree),
            encoding="utf-8"
        )

        print(f"Processed: {filepath}")

    except SyntaxError:
        print(f"Skipping invalid Python file: {filepath}")

    except Exception as e:
        print(f"Error processing {filepath}: {e}")


def find_python_files(root_path: Path):
    for path in root_path.rglob("*.py"):

        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue

        yield path


def main():
    parser = argparse.ArgumentParser(
        description="Automatically generate Python docstrings using Ollama."
    )

    parser.add_argument(
        "--path",
        required=True,
        help="Root folder path of the Python project."
    )

    parser.add_argument(
        "--model",
        default="qwen2.5-coder",
        help="Ollama model name (default: qwen2.5-coder)"
    )

    parser.add_argument(
        "--url",
        default="http://localhost:11434",
        help="Ollama API URL"
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing docstrings"
    )

    parser.add_argument(
        "--include-private",
        action="store_true",
        help="Include private functions"
    )

    args = parser.parse_args()

    root_path = Path(args.path)

    if not root_path.exists():
        print("Provided path does not exist.")
        return

    llm_client = OllamaClient(
        model=args.model,
        url=args.url,
    )

    transformer = DocstringAdder(
        llm_client=llm_client,
        overwrite_existing=args.overwrite,
        skip_private=not args.include_private,
    )

    files = list(find_python_files(root_path))

    print(f"Found {len(files)} Python files.")

    for file in files:
        process_file(file, transformer)

    print("Docstring generation complete.")


if __name__ == "__main__":
    main()
