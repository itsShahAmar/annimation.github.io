# Contributing to Funny Animation Shorts Factory

Thank you for your interest in contributing! This project thrives on community involvement — whether you are adding new comedy hooks, improving animation visuals, or fixing bugs.

## Getting Started

1. **Fork** the repository and clone your fork
2. **Create a branch** for your change: `git checkout -b feat/my-comedy-hook`
3. **Make your changes** following the guidelines below
4. **Run tests**: `python -m pytest tests/ -v`
5. **Push** and open a **Pull Request**

## Development Setup

```bash
git clone https://github.com/ShahAmar-Official/annimation.github.io
cd annimation.github.io
pip install -r requirements.txt
pip install pytest
python -m pytest tests/ -v
```

## What We Welcome

- 🎭 **New comedy hook templates** — absurd, relatable, meme-culture hooks for `src/scriptwriter.py`
- 🎬 **New body pattern styles** — fresh comedy structure patterns
- 😂 **New comedy fallback topics** — universally funny topics for `src/trending.py`
- 🖼️ **Thumbnail design improvements** — more vibrant, funny, eye-catching designs
- 🎙️ **TTS / voice enhancements** — better comedy voice selection
- 🐛 **Bug fixes** — anything that breaks the pipeline
- 📝 **Documentation** — clearer setup instructions, better examples

## Comedy Content Guidelines

Comedy content in this project must be:

- ✅ **Universally appealing** — funny to a broad audience
- ✅ **Wholesome** — no offensive, harmful, or discriminatory content
- ✅ **Meme-culture aware** — Gen-Z and millennial humour works best
- ✅ **Animation-friendly** — jokes that work visually as cartoons
- ❌ **Not targeting individuals** — no personal attacks or mockery of real people
- ❌ **Not politically divisive** — avoid hot-button political topics

## Code Style

- Follow existing code patterns (see other files in `src/`)
- Add docstrings to all public functions
- No new paid API dependencies — the pipeline must remain 100% free
- Keep `config.py` variables documented with inline comments

## Testing

All new features should include or update tests in `tests/`. Run:

```bash
python -m pytest tests/ -v
```

Tests should not make real network calls — mock external dependencies.

## Pull Request Checklist

- [ ] Tests pass: `python -m pytest tests/ -v`
- [ ] No new paid API dependencies introduced
- [ ] Docstrings added/updated
- [ ] Comedy content follows the guidelines above
- [ ] PR description explains the change clearly
