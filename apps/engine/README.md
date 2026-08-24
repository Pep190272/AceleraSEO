# AceleraSEO Engine

Autonomous SEO strategy engine: Sense, Decide, Act, Learn.

FastAPI service that reads the site's own Search Console and Analytics data,
decides what to change, applies it, and measures the result.

See the [repository README](../../README.md) for the full project overview,
architecture and setup.

## Local development

```bash
cd apps/engine
pip install -e ".[dev]"
pytest
```
