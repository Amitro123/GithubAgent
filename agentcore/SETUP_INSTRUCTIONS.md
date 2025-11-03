# RepoIntegrator Setup Instructions

## Changes Made

### 1. **Dependencies Added**
Added to `pyproject.toml`:
- `reflex` - UI framework
- `gitpython` - Git operations
- `httpx` - HTTP client for Lightning AI

### 2. **File Structure Reorganization**

#### New Structure:
```
src/repofactor/
├── domain/
│   └── models/
│       ├── __init__.py
│       ├── file_analysis.py          # Domain model for file analysis
│       └── analysis_result.py        # Domain model for analysis results
├── application/
│   └── services/
│       ├── lightning_ai_service.py   # ✓ Already existed
│       ├── repo_integrator_service.py # ✓ Created (stub)
│       └── git_service.py            # ✓ Created (stub)
└── infrastructure/
    └── ui/
        ├── __init__.py
        ├── repo_integrator_ui.py     # ✓ Moved from root
        └── app.py                    # ✓ Created

Root level:
├── app.py                            # ✓ Updated to import from new location
├── rxconfig.py                       # ✓ Kept at root (Reflex requirement)
└── pyproject.toml                    # ✓ Updated with dependencies
```

#### Old Files (can be deleted):
- `repo_integrator_ui.py` (root) - replaced by `src/repofactor/infrastructure/ui/repo_integrator_ui.py`

### 3. **Import Path Updates**
All imports have been updated to use the clean architecture structure:
- Domain models: `from repofactor.domain.models import FileAnalysis, AnalysisResult`
- Services: `from repofactor.application.services.lightning_ai_service import ...`

## Installation & Running

### Step 1: Install Dependencies
```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

### Step 2: Set Environment Variables
Create or update `.env` file:
```env
LIGHTNING_API_KEY=your_lightning_ai_api_key_here
LIGHTNING_STUDIO_URL=your_studio_url_here  # Optional
```

### Step 3: Initialize Reflex
```bash
reflex init
```

### Step 4: Run the Application
```bash
# Development mode with hot reload
reflex run

# Or production mode
reflex run --env prod
```

The application will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000

## What's Working Now

✅ **Structure**: Clean architecture with proper separation of concerns
✅ **Domain Models**: Extracted to domain layer
✅ **UI**: Reflex UI properly organized in infrastructure layer
✅ **Services**: Lightning AI service exists and is functional
✅ **Dependencies**: All required packages added to pyproject.toml

## What Still Needs Implementation

### High Priority:
1. **Git Service** (`git_service.py`)
   - Implement `clone_repository()` using GitPython
   - Implement `get_repo_structure()`
   - Implement `extract_files()`

2. **Repo Integrator Service** (`repo_integrator_service.py`)
   - Implement `analyze_integration_points()`
   - Implement `generate_integration_plan()`
   - Implement `apply_integration()`

### Medium Priority:
3. **Error Handling**: Add comprehensive error handling in UI
4. **Caching**: Implement caching layer for analysis results
5. **Testing**: Add unit and integration tests

### Low Priority:
6. **Backup Mechanism**: Implement file backup before modifications
7. **Diff Generation**: Add diff preview functionality
8. **Quota Management**: Connect to real Lightning AI quota API

## Architecture Notes

This project follows **Clean Architecture** principles:

- **Domain Layer** (`domain/`): Business entities and models
- **Application Layer** (`application/`): Use cases and services
- **Infrastructure Layer** (`infrastructure/`): External interfaces (UI, API, DB)

Benefits:
- ✅ Testable: Business logic independent of frameworks
- ✅ Flexible: Easy to swap UI or AI providers
- ✅ Maintainable: Clear separation of concerns
- ✅ Scalable: Easy to add new features

## Troubleshooting

### Issue: Import errors
**Solution**: Make sure you're running from the project root and have installed the package:
```bash
pip install -e .
```

### Issue: Reflex not found
**Solution**: Install dependencies:
```bash
uv sync
# or
pip install reflex
```

### Issue: Lightning AI errors
**Solution**: Check your `.env` file has valid `LIGHTNING_API_KEY`

## Next Steps

1. **Install dependencies**: `uv sync`
2. **Set up environment**: Create `.env` with Lightning AI credentials
3. **Run the app**: `reflex run`
4. **Implement Git service**: Start with `clone_repository()`
5. **Test the flow**: Try analyzing a simple GitHub repo

---

**Status**: ✅ Ready to run (with stub implementations)
**Last Updated**: 2024-11-03
