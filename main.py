"""CLI tool for automatically generating Python docstrings using LLMs."""

import ast
import argparse
from pathlib import Path

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
    """AST node transformer that generates and inserts docstrings into functions and methods."""

    def __init__(
        self,
        llm_client: LLMClient,
        overwrite_existing: bool = False,
        skip_private: bool = True,
    ):
        """Initialize the DocstringAdder.

        Args:
            llm_client (LLMClient): The LLM client to use for generating docstrings.
            overwrite_existing (bool): Whether to overwrite existing docstrings.
            skip_private (bool): Whether to skip private functions (starting with _).
        """
        self.llm_client = llm_client
        self.overwrite_existing = overwrite_existing
        self.skip_private = skip_private
        self.changed = False

    def process_function(self, node):
        """Generate and insert a docstring for a single function/method AST node.

        Args:
            node: The AST node representing a function or method.

        Returns:
            The AST node, potentially modified with an inserted docstring.
        """

        if self.skip_private and node.name.startswith("_"):
            return node

        if not self.overwrite_existing and ast.get_docstring(node):
            return node

        try:
            function_code = ast.unparse(node)

            print(f"Generating docstring for: {node.name}")

            docstring = self.llm_client.generate_docstring(function_code)

            # Remove existing docstring before inserting the new one
            # to prevent duplicate stacked docstrings when --overwrite is used.
            if (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            ):
                node.body.pop(0)

            node.body.insert(0, ast.Expr(value=ast.Constant(value=docstring)))
            self.changed = True

        except Exception as e:
            print(f"Failed on function '{node.name}': {e}")

        return node

    def visit_FunctionDef(self, node):
        """Visit a regular function definition node."""
        self.generic_visit(node)
        return self.process_function(node)

    def visit_AsyncFunctionDef(self, node):
        """Visit an async function definition node."""
        self.generic_visit(node)
        return self.process_function(node)


def process_file(
    filepath: Path,
    transformer: DocstringAdder,
):
    """Process a single Python file: parse, add docstrings, and write back.

    Args:
        filepath (Path): Path to the Python file to process.
        transformer (DocstringAdder): The AST transformer to apply.
    """
    try:
        source = filepath.read_text(encoding="utf-8")

        tree = ast.parse(source)

        transformer.changed = False
        updated_tree = transformer.visit(tree)

        if transformer.changed:
            ast.fix_missing_locations(updated_tree)

            filepath.write_text(ast.unparse(updated_tree), encoding="utf-8")

            print(f"Updated: {filepath}")

        else:
            print(f"Skipped unchanged file: {filepath}")

    except SyntaxError:
        print(f"Skipping invalid Python file: {filepath}")

    except Exception as e:
        print(f"Error processing {filepath}: {e}")


def find_python_files(root_path: Path):
    """Recursively find all Python files under root_path, excluding common non-source directories.

    Args:
        root_path (Path): The root directory to search.

    Yields:
        Path: Paths to Python files.
    """
    for path in root_path.rglob("*.py"):

        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue

        yield path


def main():
    """Entry point for the pydocgen CLI."""
    parser = argparse.ArgumentParser(
        description="Automatically generate Python docstrings using an LLM."
    )

    parser.add_argument(
        "--path", required=True, help="Root folder path of the Python project."
    )

    parser.add_argument(
        "--provider",
        choices=["ollama", "openai", "groq"],
        default="ollama",
        help="LLM provider to use (default: ollama)",
    )

    parser.add_argument(
        "--model",
        default=None,
        help="Model name (default for ollama: qwen2.5-coder, default for openai: gpt-4o, default for groq: llama3-8b-8192)",
    )

    parser.add_argument(
        "--url",
        default=None,
        help="API URL (default for ollama: http://localhost:11434)",
    )

    parser.add_argument(
        "--api-key",
        help="API key for cloud providers (e.g., OpenAI). Can also use environment variables like OPENAI_API_KEY.",
    )

    parser.add_argument(
        "--overwrite", action="store_true", help="Overwrite existing docstrings"
    )

    parser.add_argument(
        "--include-private", action="store_true", help="Include private functions"
    )

    args = parser.parse_args()

    root_path = Path(args.path)

    if not root_path.exists():
        print("Provided path does not exist.")
        return

    # Per-provider default models and URLs.
    # None checks reliably detect whether the user explicitly supplied a value.
    try:
        if args.provider == "ollama":
            llm_client = OllamaClient(
                model=args.model or "qwen2.5-coder",
                url=args.url or "http://localhost:11434",
            )
        elif args.provider == "openai":
            llm_client = OpenAIClient(
                model=args.model or "gpt-4o",
                api_key=args.api_key,
                base_url=args.url,  # None is fine here — OpenAI SDK uses its own default
            )
        elif args.provider == "groq":
            llm_client = GroqClient(
                model=args.model or "llama3-8b-8192",
                api_key=args.api_key,
                base_url=args.url,  # None is fine here — Groq SDK uses its own default
            )
    except ImportError as e:
        raise SystemExit(f"Error: {e}")
    except Exception as e:
        raise SystemExit(f"Error: Failed to initialize the {args.provider} client: {e}")

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
