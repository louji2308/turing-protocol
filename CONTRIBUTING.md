# Contributing to Turing Protocol

Thank you for your interest in contributing! This document outlines the workflow for submitting changes.

## How to Contribute

1. **Fork** the repository and create a branch from `main`.
2. **Make your changes** — ensure they follow the existing code style (see below).
3. **Run tests** before submitting:
   ```bash
   pytest tests/
   ```
4. **Open a Pull Request** with a clear title and description of your changes.

## Code Style

- Python: Follow [PEP 8](https://peps.python.org/pep-0008/).
- Use type annotations for all public functions and methods.
- Import order: standard library → third-party → local modules.
- Run `ruff check .` before committing.

## Commit Messages

Write concise, descriptive commit messages in the imperative mood:

```
Add gas price fallback when RPC is unreachable
Fix missing await on strategy.decide() call
```

## Reporting Issues

Open an issue on GitHub with:
- A clear summary of the problem
- Steps to reproduce (if applicable)
- Environment details (OS, Python version, dependency versions)

## Questions

Open a [GitHub Discussion](https://github.com/anomalyco/turing-protocol/discussions) or reach out to the maintainers.

By contributing, you agree that your contributions will be licensed under the MIT License.
