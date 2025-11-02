# AI Agent Guide - RepoIntegrator

> **For**: AI agents (Claude, GPT, Cursor, Copilot, Windsurf) helping develop this project

## 🎯 Quick Understanding - What Does This Project Do?

**In one sentence**: A tool that takes a GitHub repo URL and automatically integrates the code into the user's existing project.

**Concrete Example**:
```
User: "Check out this repo: github.com/microsoft/LLMLingua
       I want to use their compression algorithm in my file src/my_code.py"

System: 
1. Clones LLMLingua
2. Analyzes which parts are relevant
3. Suggests: "Need to modify 3 files: my_code.py, requirements.txt, tests/"
4. User approves
5. System automatically updates the files
```

## 🏗️ Architecture - What Already Exists

### Current Stack
```
Frontend: Reflex (Python UI framework)
Backend: FastAPI
AI Provider: Lightning AI (20 free GPU calls/month)
Code Analysis: GitPython, tree-sitter
Base Template: agent-api-cookiecutter
```

### Files Already Created
```
✅ repo_integrator_ui.py          # Reflex UI with all stages
✅ lightning_ai_service.py         # Lightning AI client & agent
✅ repo_integrator_service.py      # Integration logic
✅ langgraph_agent.py              # Optional LangGraph workflow
✅ requirements.txt                # All dependencies
✅ SPEC.md                         # Full specification
✅ Lightning_Setup_Guide.md        # Setup instructions
✅ .env.example                    # Environment template
✅ quick_start.sh                  # Installation script
```

### What's Missing (TODO)
```
❌ git_service.py                  # Git clone/operations
❌ code_parser.py                  # AST/tree-sitter parsing
❌ diff_generator.py               # Diff creation
❌ cache_manager.py                # Caching layer
❌ API routes integration          # Connect to FastAPI
❌ Tests                           # Unit & integration tests
```

## 🤖 How to Help - Instructions for AI Agents

### When User Asks: "Help me implement X"

#### Step 1: Check Context
```python
# What stage is the user at?
if "just starting" or "setup":
    # Guide through quick_start.sh
    # Help with .env configuration
    
elif "implementing feature":
    # Reference SPEC.md for requirements
    # Check existing code in services/
    
elif "debugging":
    # Check logs, error messages
    # Reference Lightning AI docs
    
elif "testing":
    # Create test cases from SPEC.md TC-001, etc.
```

#### Step 2: Follow Project Patterns

**Lightning AI Calls Pattern:**
```python
# ✅ CORRECT: Use the established pattern
from services.lightning_ai_service import LightningAIClient, LightningModel

async def my_function():
    client = LightningAIClient()
    try:
        response = await client.generate(
            prompt="...",
            model=LightningModel.CODE_LLAMA_34B
        )
        return response.text
    finally:
        await client.close()

# ❌ WRONG: Direct API calls
import httpx
response = httpx.post("https://lightning.ai/...")  # Don't do this
```

**Reflex State Pattern:**
```python
# ✅ CORRECT: Follow existing State class structure
class State(rx.State):
    # Input fields
    repo_url: str = ""
    
    # Process state
    stage: str = "input"
    is_loading: bool = False
    
    # Results
    analysis: Optional[AnalysisResult] = None
    
    async def analyze_repo(self):
        self.is_loading = True
        try:
            # ... logic
            yield  # For progress updates
        finally:
            self.is_loading = False

# ❌ WRONG: Global variables or different patterns
global_repo_url = ""  # Don't do this
```

#### Step 3: Preserve Quota Management

**CRITICAL**: Lightning AI has only 20 free calls/month

```python
# ✅ ALWAYS check quota before calling
if client.get_remaining_quota() > 0:
    await client.generate(...)
else:
    raise QuotaExceededError("Use fallback or upgrade")

# ✅ Use caching for repeated analysis
cache_key = hashlib.md5(repo_url.encode()).hexdigest()
if cached := get_from_cache(cache_key):
    return cached

# ✅ Batch operations when possible
# Instead of 5 separate calls:
for file in files:
    analyze(file)  # ❌ Bad: 5 calls

# Do this:
analyze_batch(files)  # ✅ Good: 1 call
```

### When User Asks: "Add feature X"

#### 1. Check SPEC.md First
```
Is this feature in the spec? 
  YES → Follow the acceptance criteria
  NO  → Discuss with user if needed, then add to spec
```

#### 2. Follow Implementation Phases
```
Phase 1 (MVP): Core functionality only
Phase 2: User-facing features
Phase 3: Polish & optimization
Phase 4: Advanced features

Don't mix phases! Finish MVP first.
```

#### 3. Code Structure
```python
# New feature template:

# 1. Add to services/ if backend logic
# services/new_feature_service.py
class NewFeatureService:
    """
    Clear docstring explaining what this does.
    
    Example:
        service = NewFeatureService()
        result = await service.do_something()
    """
    
    async def main_method(self) -> Dict:
        """Single responsibility, clear return type"""
        pass

# 2. Add UI component to repo_integrator_ui.py
def new_feature_component() -> rx.Component:
    """Clear component name, returns Reflex component"""
    return rx.vstack(...)

# 3. Add State methods
class State(rx.State):
    async def handle_new_feature(self):
        """Clear handler for user action"""
        pass

# 4. Add API endpoint if needed
@router.post("/api/v1/new-feature")
async def new_feature_endpoint(request: Request):
    """API documentation here"""
    pass
```

### When User Asks: "Debug this error"

#### Common Issues & Solutions

**Issue 1: Lightning AI API Error**
```python
# Error: "API key invalid" or "Connection refused"

# Check:
1. Is LIGHTNING_API_KEY in .env?
   cat .env | grep LIGHTNING_API_KEY
   
2. Is .env loaded?
   from dotenv import load_dotenv
   load_dotenv()  # Add this!
   
3. Is key format correct?
   # Should be: la-xxxxxxxxxxxxx
   # Not: Bearer la-xxx or api-xxx
```

**Issue 2: Reflex UI Not Updating**
```python
# Error: State changes but UI doesn't update

# Solution: Use yield for async updates
async def long_operation(self):
    self.progress = 25
    yield  # ✅ This updates UI
    
    await some_work()
    self.progress = 50
    yield  # ✅ This updates UI
    
    # ❌ Without yield, UI only updates at end
```

**Issue 3: Quota Exceeded**
```python
# Error: "Monthly quota exceeded"

# Solutions:
1. Check if cache is working
2. Use fallback model (OpenAI/Anthropic)
3. Wait for monthly reset
4. Suggest upgrade to user

# Show in UI:
if State.remaining_quota == 0:
    rx.callout(
        "Quota exceeded. Consider upgrading or wait for reset.",
        color_scheme="orange"
    )
```

**Issue 4: Import Errors**
```python
# Error: ModuleNotFoundError

# Check installation:
pip list | grep reflex
pip list | grep httpx

# Reinstall if needed:
pip install -r requirements.txt

# Verify Python version:
python --version  # Must be 3.10+
```

## 📝 Code Review Checklist

When reviewing or generating code, check:

### Functionality
- [ ] Follows patterns from existing code
- [ ] Uses Lightning AI client correctly
- [ ] Handles errors gracefully
- [ ] Manages quota properly
- [ ] Async/await used for I/O

### Code Quality
- [ ] Type hints on all functions
- [ ] Docstrings (Google style)
- [ ] Clear variable names
- [ ] No hardcoded values (use config/env)
- [ ] Max line length 88 chars

### User Experience
- [ ] Progress indicators for long operations
- [ ] Clear error messages
- [ ] Quota visible to user
- [ ] Responsive UI
- [ ] Loading states

### Safety
- [ ] No API keys in code
- [ ] Input validation
- [ ] No exec() or eval()
- [ ] File operations sandboxed
- [ ] Quota limits enforced

## 🎓 Examples for Common Tasks

### Example 1: Add New Analysis Feature

```python
# User request: "Add support for analyzing dependencies"

# Step 1: Add to lightning_ai_service.py
class CodeAnalysisAgent:
    async def analyze_dependencies(
        self, 
        repo_content: Dict[str, str]
    ) -> List[str]:
        """
        Extract dependencies from repository files.
        
        Args:
            repo_content: Dict of {filepath: content}
            
        Returns:
            List of dependency package names
        """
        prompt = f"""
        Analyze these files and list all external dependencies:
        {repo_content}
        
        Return JSON: {{"dependencies": ["package1", "package2"]}}
        """
        
        response = await self.client.generate(
            prompt=prompt,
            model=self.model,
            max_tokens=500
        )
        
        # Parse and return
        result = self._parse_json(response.text)
        return result.get("dependencies", [])

# Step 2: Add to UI state
class State(rx.State):
    dependencies: List[str] = []
    
    async def analyze_repo(self):
        # ... existing code ...
        
        # Add dependency analysis
        agent = CodeAnalysisAgent()
        self.dependencies = await agent.analyze_dependencies(repo_content)
        
# Step 3: Display in UI
def reviewing_stage() -> rx.Component:
    return rx.vstack(
        # ... existing components ...
        
        # Add dependencies section
        rx.heading("Dependencies", size="5"),
        rx.foreach(
            State.dependencies,
            lambda dep: rx.badge(dep, color_scheme="blue")
        )
    )
```

### Example 2: Add Caching

```python
# User request: "Cache analyses to save quota"

# Step 1: Create cache_manager.py
import hashlib
import json
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime, timedelta

class CacheManager:
    """Manages caching of repo analyses."""
    
    def __init__(self, cache_dir: str = "./cache", ttl_hours: int = 24):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.ttl = timedelta(hours=ttl_hours)
    
    def get(self, repo_url: str) -> Optional[Dict]:
        """Get cached analysis if exists and not expired."""
        cache_key = self._get_key(repo_url)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if not cache_file.exists():
            return None
        
        # Check if expired
        file_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
        if datetime.now() - file_time > self.ttl:
            cache_file.unlink()
            return None
        
        with open(cache_file) as f:
            return json.load(f)
    
    def set(self, repo_url: str, data: Dict):
        """Cache analysis result."""
        cache_key = self._get_key(repo_url)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        with open(cache_file, "w") as f:
            json.dump(data, f, indent=2)
    
    def _get_key(self, repo_url: str) -> str:
        """Generate cache key from repo URL."""
        return hashlib.md5(repo_url.encode()).hexdigest()

# Step 2: Use in service
async def analyze_repo_with_lightning(
    repo_url: str,
    ...
) -> Dict:
    cache = CacheManager()
    
    # Try cache first
    if cached := cache.get(repo_url):
        return cached
    
    # Not in cache, analyze
    result = await agent.analyze_repository(...)
    
    # Cache result
    cache.set(repo_url, result)
    
    return result
```

### Example 3: Add Git Integration

```python
# User request: "Create a branch with changes"

# Step 1: Create git_service.py
import git
from pathlib import Path
from typing import Optional

class GitService:
    """Handles Git operations."""
    
    def __init__(self, repo_path: str = "."):
        self.repo = git.Repo(repo_path)
    
    def create_integration_branch(
        self, 
        repo_name: str,
        base_branch: str = "main"
    ) -> str:
        """
        Create a new branch for integration.
        
        Args:
            repo_name: Name of integrated repo
            base_branch: Base branch to branch from
            
        Returns:
            Name of created branch
        """
        # Create branch name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        branch_name = f"integrate/{repo_name}/{timestamp}"
        
        # Create and checkout branch
        current = self.repo.active_branch
        new_branch = self.repo.create_head(branch_name, base_branch)
        new_branch.checkout()
        
        return branch_name
    
    def commit_changes(
        self,
        message: str,
        files: List[str]
    ):
        """Commit specific files."""
        self.repo.index.add(files)
        self.repo.index.commit(message)
    
    def create_pr_info(self) -> Dict:
        """Generate PR information."""
        return {
            "branch": self.repo.active_branch.name,
            "base": "main",
            "title": f"Integration: {self.repo.active_branch.name}",
            "body": "Automated integration by RepoIntegrator"
        }

# Step 2: Integrate with apply_changes
class State(rx.State):
    async def apply_changes(self):
        # ... apply file changes ...
        
        # Create Git branch
        git_service = GitService()
        branch = git_service.create_integration_branch(
            repo_name="microsoft-llmlingua"
        )
        
        # Commit changes
        git_service.commit_changes(
            message="Integrate compression algorithm",
            files=self.selected_files
        )
        
        # Show PR info
        pr_info = git_service.create_pr_info()
        self.success_message = (
            f"Changes committed to branch: {branch}\n"
            f"Ready to create PR!"
        )
```

## 🚨 Critical Rules

### NEVER DO:
1. ❌ Hardcode API keys in code
2. ❌ Make Lightning AI calls without checking quota
3. ❌ Use exec() or eval() on user input
4. ❌ Write files outside project directory
5. ❌ Skip error handling on async operations
6. ❌ Ignore type hints
7. ❌ Create global state
8. ❌ Mix sync and async incorrectly

### ALWAYS DO:
1. ✅ Check SPEC.md before implementing
2. ✅ Follow existing code patterns
3. ✅ Add docstrings to all functions
4. ✅ Use type hints
5. ✅ Handle errors gracefully
6. ✅ Update progress for long operations
7. ✅ Test with small repos first
8. ✅ Cache when possible

## 📚 Reference Links

Quick access to documentation:

- **This Project**: `/SPEC.md` - Full specification
- **Lightning AI**: https://lightning.ai/docs
- **Reflex**: https://reflex.dev/docs
- **FastAPI**: https://fastapi.tiangolo.com
- **GitPython**: https://gitpython.readthedocs.io

## 🎯 Current Priorities

Based on implementation checklist in SPEC.md:

### Now (Phase 1 - MVP):
1. Implement git_service.py
2. Improve code parsing (AST/tree-sitter)
3. Add basic tests
4. Test with 3-5 real repos

### Next (Phase 2):
1. Better diff visualization
2. Improved prompts
3. Error recovery
4. Documentation

### Later (Phase 3+):
1. VSCode extension
2. CLI tool
3. Multi-repo support
4. Collaborative features

---

**Remember**: This guide is for AI assistants. Keep it updated as the project evolves!

**Last Updated**: 2024-03-01  
**Status**: 🚧 Active Development