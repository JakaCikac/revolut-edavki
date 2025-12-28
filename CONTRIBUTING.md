# Contributing to revolut-edavki

Thank you for your interest in contributing to revolut-edavki! This document provides guidelines for contributing to the project.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for all contributors.

## How to Contribute

### Reporting Bugs

1. **Check existing issues** to avoid duplicates
2. **Use the bug report template** (if available)
3. **Include details:**
   - Python version
   - Operating system
   - Steps to reproduce
   - Expected vs actual behavior
   - Error messages and logs
   - Sample data (anonymized)

### Suggesting Features

1. **Check existing feature requests** to avoid duplicates
2. **Describe the use case** clearly
3. **Explain the benefit** to users
4. **Consider implementation complexity**

### Submitting Pull Requests

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Make your changes**
4. **Write/update tests**
5. **Update documentation**
6. **Run tests** (`poetry run pytest`)
7. **Commit with clear messages**
8. **Push to your fork**
9. **Open a Pull Request**

## Development Setup

### Prerequisites
- Python 3.12+
- Poetry
- Docker (optional)

### Setup Steps

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/revolut-edavki.git
cd revolut-edavki

# Install dependencies
poetry install

# Set up environment
cp .env.example .env
# Edit .env with your settings

# Run tests
poetry run pytest tests/

# Run the application
poetry run python server.py
```

## Coding Standards

### Python Style
- Follow PEP 8
- Use type hints where appropriate
- Maximum line length: 100 characters
- Use meaningful variable names
- Add docstrings to functions

### Example
```python
def calculate_tax(amount: float, rate: float) -> float:
    """Calculate tax amount.
    
    Args:
        amount: Taxable amount in EUR
        rate: Tax rate as decimal (e.g., 0.25 for 25%)
    
    Returns:
        Tax amount in EUR
    """
    return amount * rate
```

### Testing
- Write tests for new features
- Maintain or improve code coverage
- Test edge cases and error conditions
- Use descriptive test names

### Example Test
```python
def test_calculate_tax_positive_amount():
    """Test tax calculation with positive amount"""
    result = calculate_tax(100.0, 0.25)
    assert result == 25.0
```

## Commit Messages

Use clear, descriptive commit messages:

```
feat: Add support for multiple brokers
fix: Correct FX rate calculation for GBP
docs: Update installation instructions
test: Add tests for dividend processing
refactor: Simplify XML generation logic
```

### Format
- **feat:** New feature
- **fix:** Bug fix
- **docs:** Documentation changes
- **test:** Test additions/changes
- **refactor:** Code refactoring
- **style:** Code style changes
- **chore:** Maintenance tasks

## Testing Guidelines

### Running Tests
```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=revolut_edavki

# Run specific test file
poetry run pytest tests/test_converter.py

# Run specific test
poetry run pytest tests/test_converter.py::test_clean_amount_eur
```

### Writing Tests
- Place tests in `tests/` directory
- Name test files `test_*.py`
- Name test functions `test_*`
- Use fixtures for common setup
- Mock external dependencies

## Documentation

### Code Documentation
- Add docstrings to all public functions
- Include parameter types and return types
- Provide usage examples for complex functions
- Document exceptions that may be raised

### README Updates
- Update README.md for new features
- Add examples for new functionality
- Update installation instructions if needed
- Keep feature list current

## Security

### Reporting Security Issues
- **DO NOT** open public issues for security vulnerabilities
- See [SECURITY.md](SECURITY.md) for reporting process
- Allow time for fixes before public disclosure

### Security Considerations
- Never commit secrets or credentials
- Validate all user inputs
- Use secure coding practices
- Review dependencies for vulnerabilities

## Review Process

### What We Look For
- ✅ Code quality and style
- ✅ Test coverage
- ✅ Documentation
- ✅ Security considerations
- ✅ Performance impact
- ✅ Backward compatibility

### Timeline
- Initial review: Within 1 week
- Feedback provided on all PRs
- May request changes before merging
- Be patient and responsive to feedback

## Areas for Contribution

### High Priority
- Production deployment improvements
- Security enhancements
- Test coverage expansion
- Documentation improvements

### Medium Priority
- Support for additional brokers
- UI/UX improvements
- Performance optimizations
- Error message improvements

### Low Priority
- Internationalization
- Additional export formats
- Advanced features

## Questions?

- **General questions:** Open a GitHub Discussion
- **Bug reports:** Open an Issue
- **Feature requests:** Open an Issue with [Feature Request] tag
- **Security concerns:** See SECURITY.md

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Recognition

Contributors will be acknowledged in:
- GitHub contributors list
- Release notes (for significant contributions)
- README.md (for major features)

Thank you for contributing to revolut-edavki! 🎉
