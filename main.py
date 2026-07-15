import ast
import argparse
from pathlib import Path
import re

from clients import LLMClient, OllamaClient, OpenAIClient, GroqClient


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


class DocstringAdder(ast.NodeTransformer):

    def __init__(
        self,
        llm_client: LLMClient,
        overwrite_existing: bool = False,
        skip_private: bool = True,
    ):
        self.llm_client = llm_client
        self.overwrite_existing = overwrite_existing
        self.skip_private = skip_private
        self.changed = False

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
            self.changed = True

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

        transformer.changed = False
        updated_tree = transformer.visit(tree)

        if transformer.changed:
            ast.fix_missing_locations(updated_tree)

            filepath.write_text(
                ast.unparse(updated_tree),
                encoding="utf-8"
            )

            print(f"Updated: {filepath}")

        else:
            print(f"Skipped unchanged file: {filepath}")

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
        description="Automatically generate Python docstrings using an LLM."
    )

    parser.add_argument(
        "--path",
        required=True,
        help="Root folder path of the Python project."
    )
    
    parser.add_argument(
        "--provider",
        choices=["ollama", "openai", "groq"],
        default="ollama",
        help="LLM provider to use (default: ollama)"
    )

    parser.add_argument(
        "--model",
        default="qwen2.5-coder",
        help="Model name (default for ollama: qwen2.5-coder, default for openai: gpt-4o, default for groq: llama3-8b-8192)"
    )

    parser.add_argument(
        "--url",
        default="http://localhost:11434",
        help="API URL (default for ollama: http://localhost:11434)"
    )
    
    parser.add_argument(
        "--api-key",
        help="API key for cloud providers (e.g., OpenAI). Can also use environment variables like OPENAI_API_KEY."
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

    if args.provider == "ollama":
        llm_client = OllamaClient(
            model=args.model,
            url=args.url,
        )
    elif args.provider == "openai":
        # Adjust defaults if the user didn't override them but switched to openai
        model = "gpt-4o" if args.model == "qwen2.5-coder" else args.model
        url = None if args.url == "http://localhost:11434" else args.url
        llm_client = OpenAIClient(
            model=model,
            api_key=args.api_key,
            base_url=url,
        )
    elif args.provider == "groq":
        model = "llama3-8b-8192" if args.model == "qwen2.5-coder" else args.model
        llm_client = GroqClient(
            model=model,
            api_key=args.api_key,
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
