# Contributing Guide

Thank you for considering contributing to Codex Subagents! We welcome all forms of contributions.

## How to Contribute

### Reporting Issues

If you find a bug or have a feature suggestion:

1. First check [Issues](https://github.com/mgoulart/codex-subagents/issues) to ensure it hasn't been reported
2. Create a new Issue using the appropriate template
3. Provide as much detail as possible:
   - Clear title and description
   - Steps to reproduce (for bugs)
   - Expected vs actual behavior
   - System environment information
   - Relevant logs or screenshots

### Submitting Code

1. **Fork the Repository**
   ```bash
   git clone https://github.com/your-username/codex-subagents.git
   cd codex-subagents
   ```

2. **Create a Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-fix-name
   ```

3. **Make Your Changes**
   - Follow existing code style
   - Update relevant documentation
   - If adding new features, update both EN/ZH documentation

4. **Commit Your Changes**
   ```bash
   git add .
   git commit -m "type: brief description

   Detailed explanation of your changes

   Closes #issue-number (if applicable)"
   ```

   Commit types:
   - `feat`: New feature
   - `fix`: Bug fix
   - `docs`: Documentation update
   - `style`: Code formatting (no functional changes)
   - `refactor`: Refactoring
   - `test`: Test related
   - `chore`: Build process or auxiliary tools

5. **Push to Your Fork**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create a Pull Request**
   - Create PR on GitHub
   - Fill in the PR template
   - Wait for review

## Documentation Contributions

Documentation improvements are equally important:

- Fix typos or grammar
- Improve clarity of explanations
- Add usage examples
- Translate documentation

**Note**: When updating documentation, please update both EN/ZH versions where applicable.

## Code Review Process

1. Maintainers will review your PR
2. Changes may be requested
3. Once approved, your code will be merged
4. Your contribution will be listed in the CHANGELOG

## Development Guidelines

### File Organization

- Command files: `commands/codex-subagents.md` (Chinese), `commands/codex-subagents-en.md` (English)
- Documentation: `README.md`, `README-en.md`, `README-zh.md`
- Log directory: `.codex-temp/` (gitignored)
- Patched server: `codex-as-mcp-patched/server.py`

### Documentation Style

- Use clear, concise language
- Provide practical code examples
- Use Markdown formatting
- Keep EN/ZH versions synchronized where maintained

## Code of Conduct

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## Need Help?

- Look for `good first issue` labels in [Issues](https://github.com/mgoulart/codex-subagents/issues)
- Ask questions in Discussions
- Check existing Pull Requests for best practices

---

Thank you for contributing!
