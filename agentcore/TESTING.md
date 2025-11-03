# Testing Guide for RepoIntegrator

## Running Tests

### Run all tests
```bash
cd C:\Users\Dana\githubagent\GithubAgent
pytest agentcore/tests/ -v
```

### Run specific test file
```bash
pytest agentcore/tests/test_agent_basic.py -v -s
```

### Run with coverage
```bash
pytest agentcore/tests/ --cov=src --cov-report=html
```

## Test Structure

```
agentcore/
├── tests/
│   ├── conftest.py          # Pytest configuration (path setup, env vars)
│   └── test_agent_basic.py  # Basic unit tests with mocks
└── src/
    └── repofactor/
        ├── application/
        │   └── services/
        │       ├── git_service.py
        │       ├── repo_integrator_service.py
        │       └── lightning_ai_service.py
        └── domain/
            └── models/
```

## What's Tested

### ✅ GitService
- URL parsing (`_extract_repo_info`)
- Listing Python files
- File reading

### ✅ AgentCore
- Initialization
- Listing Python files in repo

### ✅ RepoIntegratorService
- Service initialization
- Full analysis flow with mocked Lightning AI

## Environment Setup

Tests use mocked environment variables set in `conftest.py`:
- `LIGHTNING_API_KEY=test-key-for-mocking`
- `REPO_CACHE_DIR=./test_cache`

## Common Issues

### ModuleNotFoundError
**Problem:** `ModuleNotFoundError: No module named 'src'`

**Solution:** Make sure you're running pytest from the project root:
```bash
cd C:\Users\Dana\githubagent\GithubAgent
pytest agentcore/tests/test_agent_basic.py -v
```

### Import Errors
**Problem:** Can't import from `agentcore.src`

**Solution:** The correct import path is just `src.repofactor...`, not `agentcore.src...`

## Next Steps

1. **Add integration tests** - Test with real Lightning AI API (optional)
2. **Add more unit tests** - Cover edge cases
3. **Add E2E tests** - Test full workflow with real repos
4. **Add performance tests** - Measure analysis speed

## Test Coverage Goals

- [ ] Git operations: 80%+
- [ ] Service layer: 90%+
- [ ] Domain models: 100%
- [ ] API endpoints: 85%+
