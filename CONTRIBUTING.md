# Contributing to SaferTrade

Thank you for your interest in contributing to SaferTrade. This document provides guidelines for contributing to the project.

## Getting Started

1. Fork the repository
2. Clone your fork locally
3. Create a feature branch: `git checkout -b feature/your-feature-name`
4. Set up the development environment:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Development Guidelines

### Code Standards

- Follow PEP 8 Python style guidelines
- Use type hints for function signatures
- Write docstrings for public functions and classes
- Keep functions focused and single-purpose

### Data Principles

- Use real data sources only; avoid mocking or synthetic data in detection logic
- Connect to actual blockchain RPCs and data providers
- Maintain data integrity and accuracy

### Path Handling

- Use `ROOT_DIR` from `shared/paths.py` for file paths
- Avoid hardcoded absolute paths

### Commit Messages

Follow the Conventional Commits specification:

- `feat:` — New feature
- `fix:` — Bug fix
- `docs:` — Documentation changes
- `refactor:` — Code refactoring
- `test:` — Adding or updating tests
- `chore:` — Maintenance tasks

Examples:
```
feat: add Base chain support to honeypot checker
fix: correct gas estimation in transaction analyzer
docs: update API endpoint documentation
```

## Testing

Run tests before submitting changes:

```bash
python -m pytest tests/
```

- Add tests for new functionality
- Maintain test coverage
- Use descriptive test names

## Pull Request Process

1. Ensure all tests pass
2. Update documentation if needed
3. Create a pull request with:
   - Clear description of changes
   - Reference to related issues
   - Summary of testing performed

4. Address review feedback promptly
5. Keep pull requests focused and reasonably sized

## Areas to Contribute

- **Engines**: Improve detection logic, add health endpoints, optimize performance
- **Schemas**: Enhance signal schemas, maintain version discipline
- **Documentation**: Expand guides, clarify setup procedures
- **Tests**: Add unit and integration tests
- **CI/CD**: Improve GitHub Actions workflows

## License

By contributing, you agree that your contributions will be licensed under the project's BUSL-1.1 license. Production use of SaferTrade requires a commercial license.

## Questions

Open an issue or start a discussion if you have questions about contributing.
