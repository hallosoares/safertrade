# Contributing

Thank you for your interest in contributing to SaferTrade. This project focuses on real DeFi threat detection and intelligence. Please keep changes factual and avoid synthetic data.

Areas to contribute:
- Engines: improve detection logic, add health endpoints, optimize async flows
- Schemas: enhance `schemas/signals_v1.json`, keep `schema_v` discipline across outputs
- API: add endpoints, improve OpenAPI descriptions, response models
- Documentation: expand `docs/engines/` and `docs/GETTING_STARTED.md`, clarify setup and troubleshooting
- Tests: add unit/integration tests for engines and API models
- CI: GitHub Actions for lint (ruff), security (bandit), and test runs

Guidelines:
- Follow BUSL-1.1 licensing; production use requires commercial license
- Use `ROOT_DIR` from `shared/paths.py` for file paths; avoid hardcoded absolute paths
- Avoid mocking real data; connect to real sources where possible
- Keep commit messages using Conventional Commits (feat, fix, docs, refactor)
- Run linters and tests locally before opening a PR
# Contributing to SaferTrade

## Getting Started

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Set up the development environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

## Development Workflow

### Code Standards
- Follow PEP 8 Python style guidelines
- Use type hints where appropriate
- Write docstrings for all public functions and classes
- Maintain test coverage above 80%

### Testing
- Run tests before submitting: `python -m pytest tests/`
- Add tests for new features in `tests/` directory
- Use descriptive test names: `test_function_name_expected_behavior`

### Commit Messages
Follow Conventional Commits specification:
- `feat: add new trading signal analyzer`
- `fix: correct calculation error in risk validator`
- `docs: update API documentation`
- `refactor: simplify main execution loop`

## Submitting Changes

1. Ensure all tests pass
2. Update documentation if needed
3. Create a pull request with:
   - Clear description of changes
   - Link to related issues
   - Screenshots/examples if UI changes

## Code Review Process

- All PRs require at least one review
- Address feedback promptly
- Keep PRs focused and small when possible

## Questions?

Open an issue or reach out to the maintainers.
