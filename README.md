# pydocgen

A command-line tool that walks through a Python project and automatically generates Google-style docstrings for every function and method. It supports multiple LLM providers including [Ollama](https://ollama.com) (default), OpenAI, and Groq.

When using Ollama (the default provider), no data leaves your machine, no API keys are required, and there are no rate limits. When using OpenAI or Groq, your source code is sent to the selected provider's API and requires valid API credentials.

---

## How it works

The tool parses each Python file using the `ast` module, identifies functions and methods that are missing docstrings, converts them back into source code, and sends that source to the configured LLM provider (Ollama, OpenAI, or Groq). The generated docstring is inserted into the syntax tree, and the updated file is written back to disk.

Supports:

- regular functions
- async functions
- class methods

Skips private methods by default, and will not overwrite existing docstrings unless you explicitly ask it to.

**Important — read before running:** because files are rewritten via `ast.unparse`, the process has side effects beyond formatting. It will also strip all inline comments and alter spacing throughout the file. This is inherent to how AST round-tripping works in Python, not a bug. Run `black .` immediately after (see the "After running" section below) and review the diff before committing.

---

## Prerequisites

### Python

Python 3.12 or higher is recommended. The tool relies on `ast.unparse`, which was introduced in Python 3.9, so that is the minimum.

### LLM Providers

#### Ollama (Default, Local)

You need Ollama installed and running locally before using this tool with the default provider.

- Download Ollama: https://ollama.com/download
- Browse available models: https://ollama.com/library

Once installed, pull a model. A few good options for code tasks:

```bash
ollama pull qwen2.5-coder  # recommended for best code/docstring quality
ollama pull codellama      # fine-tuned for code
ollama pull deepseek-coder # strong alternative for code understanding
```

Verify Ollama is running before you proceed:

```bash
curl http://localhost:11434
```

#### OpenAI (Cloud)

To use OpenAI, install the optional dependency and provide an API key using either the `--api-key` argument or the `OPENAI_API_KEY` environment variable.

```bash
pip install "pydocgen[openai]"
# or with uv
uv add "pydocgen[openai]"
```

#### Groq (Cloud)

To use Groq, install the optional dependency and provide an API key using either the `--api-key` argument or the `GROQ_API_KEY` environment variable.

```bash
pip install "pydocgen[groq]"
# or with uv
uv add "pydocgen[groq]"
```

---

## Installation

Clone the repository and install dependencies. If you use `uv` (recommended):

```bash
git clone https://github.com/LordZeusIsBack/pydocgen.git
cd pydocgen

uv sync
```

If you prefer plain pip:

```bash
pip install -r requirements.txt
```

---

## Example

Before:

```python
def add(a: int, b: int) -> int:
    return a + b
```

After:

```python
def add(a: int, b: int) -> int:
    """Adds two integers.

    Args:
        a (int): First integer.
        b (int): Second integer.

    Returns:
        int: Sum of the two integers.
    """
    return a + b
```

---

## Usage

```bash
python main.py --path /path/to/your/project
```

This will scan every `.py` file under the given path, skip private functions (those starting with `_`), and add docstrings to any function that does not already have one.

### Full options

```text
--path             Path to the root of the Python project (required)
--provider         LLM provider to use: 'ollama', 'openai', or 'groq' (default: ollama)
--model            Model name (provider-specific defaults are used if omitted)
--url              API URL (default for ollama: http://localhost:11434)
--api-key          API key for cloud providers. Can also use environment variables like OPENAI_API_KEY or GROQ_API_KEY.
--overwrite        Overwrite docstrings that already exist
--include-private  Also generate docstrings for private functions and methods
```

### Examples

Use a different model:

```bash
python main.py --path ./myproject --model codellama
```

Regenerate all docstrings from scratch, including ones that already exist:

```bash
python main.py --path ./myproject --overwrite
```

Include private methods:

```bash
python main.py --path ./myproject --include-private
```

Point to a remote or non-default Ollama instance:

```bash
python main.py --path ./myproject --url http://192.168.1.10:11434
```

Use OpenAI as the provider:

```bash
export OPENAI_API_KEY="sk-..."
python main.py --path ./myproject --provider openai --model gpt-4o
```

Use Groq as the provider:

```bash
export GROQ_API_KEY="gsk_..."
python main.py --path ./myproject --provider groq --model llama3-8b-8192
```

---

## What gets skipped

The following directories are never traversed:

- `.git`
- `__pycache__`
- `.venv`, `venv`, `env`
- `node_modules`
- `.mypy_cache`
- `.pytest_cache`

Files with syntax errors are skipped with a warning rather than crashing the run.

---

## After running

Once the tool finishes, run `black` on your project before reviewing or committing anything:

```bash
black .
```

This is not optional. The tool writes files back using `ast.unparse`, which produces valid Python but strips all original formatting — blank lines, spacing preferences, everything. Black restores it to a consistent, readable state. `black` is already included in the dependencies so nothing extra needs to be installed.

---

## A note on output formatting

The generated docstrings follow Google style. The model is instructed to include an `Args` section, a `Returns` section, and a `Raises` section only when relevant. Empty sections are omitted. The temperature is set low (0.1) intentionally — you want consistency here, not creativity.

That said, LLM output is never perfectly deterministic. Review the results before committing them, especially for complex functions where the model might misread intent.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.