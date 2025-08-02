# Local Development Guide (with uv)

This project uses [uv](https://github.com/astral-sh/uv) for fast, reproducible Python workflows.

## Quick Start

1. **Install uv**  

   ```sh
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Create a virtual environment**  

   ```sh
   uv venv
   ```

3. **Activate the environment**  

   ```sh
   source .venv/bin/activate
   ```

4. **Install dependencies**  

   ```sh
   uv pip sync requirements-dev.txt
   ```

5. **Run tests and linting**  

   ```sh
   uv run pytest
   uv run ruff check .
   ```

## Notes

- Use `uv pip sync requirements.txt` for production dependencies only.
- All CI steps use `uv` for consistency.
- For more, see [uv documentation](https://github.com/astral-sh/uv).
