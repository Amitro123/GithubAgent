# RepoIntegrator - Project Specification

> **Description**: Automated tool for intelligent integration of GitHub repositories into existing projects using AI agents

## 📋 Overview

### Problem Statement
Developers frequently discover excellent repositories on GitHub that could help them, but integrating them requires:
- Deep understanding of the source code
- Dependency mapping
- Adaptation to existing architecture
- Changes across multiple files
- Handling conflicts

**The Solution**: A tool that automatically analyzes the repo, plans the integration, and generates the necessary code changes.

### Product Goal
Reduce integration time from days/hours to 10-15 minutes.

## 🎯 User Stories

### US-001: Basic Repo Analysis
**As a** developer  
**I want to** enter a GitHub repository URL  
**So that** the system analyzes it and suggests an integration plan

**Acceptance Criteria:**
- [ ] Input field for GitHub URL with validation
- [ ] Support for public repos
- [ ] Analyze repo structure (files, dependencies)
- [ ] Identify core modules
- [ ] Response time < 60 seconds

### US-002: Custom Configuration
**As a** developer  
**I want to** specify my target file and provide free-form instructions  
**So that** the integration is tailored exactly to my needs

**Acceptance Criteria:**
- [ ] Optional field for target file
- [ ] Text area for free-form instructions
- [ ] Support for English and Hebrew
- [ ] Context understanding from instructions

### US-003: Plan Review
**As a** developer  
**I want to** see a detailed list of affected files before execution  
**So that** I can approve or reject specific changes

**Acceptance Criteria:**
- [ ] List of files with confidence scores
- [ ] Explanation for why each file needs changes
- [ ] Ability to check/uncheck files
- [ ] Warnings about potential risks
- [ ] Display of dependencies to be added

### US-004: Apply Changes
**As a** developer  
**I want to** approve the plan and apply the changes  
**So that** my code is automatically updated

**Acceptance Criteria:**
- [ ] Apply changes only to selected files
- [ ] Backup original files
- [ ] Real-time progress indicator
- [ ] Success/failure at file level
- [ ] Rollback on error

### US-005: Model Selection
**As a** developer  
**I want to** choose different AI models (CodeLlama, DeepSeek, etc.)  
**So that** I can balance quality, speed, and quota

**Acceptance Criteria:**
- [ ] Dropdown with model list
- [ ] Brief description for each model
- [ ] Display remaining quota
- [ ] Warning when quota is low

## 🏗️ Architecture

### Technology Stack

```yaml
Frontend:
  Framework: Reflex (Python-based)
  Styling: Tailwind CSS (via Reflex)
  State Management: Reflex State
  
Backend:
  Framework: FastAPI
  Agent Framework: LangGraph (optional, for complex flows)
  HTTP Client: httpx
  
AI/ML:
  Primary: Lightning AI (GPU inference)
  Models:
    - CodeLlama 34B (default)
    - DeepSeek Coder 33B
    - StarCoder2 15B
  Fallback: OpenAI GPT-4 / Anthropic Claude
  
Tools:
  Git: GitPython
  Code Analysis: tree-sitter, AST parsing
  Diff Generation: unidiff
  
Infrastructure:
  Deployment: Docker
  CI/CD: GitHub Actions
  Monitoring: (TBD - Sentry/Posthog)
```

### File Structure

```
repo_integrator/
├── repo_integrator_ui.py          # Reflex UI main file
├── services/
│   ├── lightning_ai_service.py    # Lightning AI integration
│   ├── repo_integrator_service.py # Core integration logic
│   └── git_service.py             # Git operations
├── agents/
│   ├── repo_integrator_agent.py   # LangGraph agent (optional)
│   └── code_analysis_agent.py     # Code analysis logic
├── utils/
│   ├── code_parser.py             # AST/tree-sitter parsing
│   ├── diff_generator.py          # Generate diffs
│   └── cache_manager.py           # Caching layer
├── api/
│   ├── main.py                    # FastAPI app
│   └── routes.py                  # API endpoints
├── tests/
│   ├── test_lightning_ai.py
│   ├── test_integration.py
│   └── test_ui.py
├── cache/                         # Cached analyses
├── logs/                          # Application logs
├── .env                           # Environment variables
├── requirements.txt
├── SPEC.md                        # This file
└── README.md
```

## 🔄 Workflows

### Flow 1: Repo Analysis

```
┌─────────────────┐
│ User inputs     │
│ - Repo URL      │
│ - Target file   │
│ - Instructions  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Clone repo      │
│ (GitPython)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Extract files   │
│ & structure     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Analyze with    │
│ Lightning AI    │
│ (CodeLlama 34B) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Parse response  │
│ - Files list    │
│ - Dependencies  │
│ - Risks         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Display plan    │
│ to user         │
└─────────────────┘
```

### Flow 2: Apply Changes

```
┌─────────────────┐
│ User selects    │
│ files to modify │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ For each file:  │
│                 │
│ 1. Load original│
│ 2. Call LLM for │
│    modifications│
│ 3. Generate diff│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Backup original │
│ files           │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Apply changes   │
│ (atomic writes) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Verify success  │
│ & notify user   │
└─────────────────┘
```

## 🎨 UI Components

### 1. Input Form (Stage: input)
```
┌────────────────────────────────────┐
│  ⚡ RepoIntegrator                 │
│  Powered by Lightning AI           │
│                                    │
│  [⚡ 18/20 calls remaining]        │
│                                    │
│  🖥️ Select model:                  │
│  [▼ CodeLlama 34B ▼]              │
│  ℹ️ Best for code integration      │
│                                    │
│  📎 GitHub Repo URL:               │
│  [________________________]        │
│                                    │
│  📄 Target file (optional):        │
│  [________________________]        │
│                                    │
│  ✍️ Instructions:                  │
│  [________________________]        │
│  [________________________]        │
│  [________________________]        │
│                                    │
│  [  🚀 Analyze with Lightning AI  ]│
└────────────────────────────────────┘
```

### 2. Analysis Progress (Stage: analyzing)
```
┌────────────────────────────────────┐
│         🔄                         │
│   Cloning repo from GitHub...      │
│   Running on Lightning AI GPU ☁️   │
│                                    │
│   ▓▓▓▓▓▓▓▓▓░░░░░░░░ 45%          │
└────────────────────────────────────┘
```

### 3. Review Plan (Stage: reviewing)
```
┌────────────────────────────────────┐
│  ℹ️ Integration Plan               │
│  Basic changes in 3 functions,     │
│  adding async support              │
│                                    │
│  📋 Affected files:                │
│  ┌──────────────────────────────┐ │
│  │ ☑️ src/compression.py        │ │
│  │   Main file for changes      │ │
│  │   [100%]                     │ │
│  └──────────────────────────────┘ │
│  ┌──────────────────────────────┐ │
│  │ ☑️ src/utils/tokenizer.py    │ │
│  │   Uses compression functions │ │
│  │   [85%]                      │ │
│  └──────────────────────────────┘ │
│                                    │
│  ⚠️ Watch out:                     │
│  • API changes may break code      │
│  • Check Python 3.8+ compatibility│
│                                    │
│  [  ⬅️ Back  ]  [  ✅ Apply Changes ]│
└────────────────────────────────────┘
```

## 🔌 API Endpoints

### POST /api/v1/analyze-repo
**Purpose**: Analyze repository
**Request:**
```json
{
  "repo_url": "https://github.com/user/repo",
  "target_file": "src/main.py",
  "instructions": "integrate compression algorithm",
  "model": "CODE_LLAMA_34B"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "main_file": "src/main.py",
    "affected_files": [
      {
        "path": "src/compression.py",
        "reason": "Main file for changes",
        "confidence": 95,
        "changes_needed": ["Add async support"]
      }
    ],
    "dependencies": ["torch", "transformers"],
    "risks": ["Check version compatibility"],
    "estimated_time": "10 minutes"
  },
  "quota_remaining": 19
}
```

### POST /api/v1/apply-changes
**Purpose**: Apply changes
**Request:**
```json
{
  "files": [
    {
      "path": "src/compression.py",
      "instructions": "convert to async"
    }
  ],
  "dry_run": false
}
```

**Response:**
```json
{
  "success": true,
  "results": [
    {
      "file": "src/compression.py",
      "status": "modified",
      "backup_path": ".backup/compression.py.20240301_120000",
      "diff": "... unified diff ..."
    }
  ]
}
```

## 🤖 AI Prompts

### Prompt 1: Repository Analysis
```
You are an expert code integration assistant analyzing a GitHub repository.

REPOSITORY: {repo_url}
USER INSTRUCTIONS: {instructions}
TARGET FILE: {target_file}

SOURCE FILES:
--- main.py ---
{file_content}
...

Analyze and provide a JSON response:
{
  "main_modules": ["list of key modules"],
  "dependencies": ["required packages"],
  "affected_files": [
    {
      "path": "file path",
      "reason": "why changes needed",
      "confidence": 85,
      "changes": ["specific changes"]
    }
  ],
  "risks": ["potential issues"],
  "implementation_steps": ["ordered steps"]
}

Focus on:
1. Integration points in target file
2. Required dependencies
3. Potential conflicts
4. Security concerns
```

### Prompt 2: Code Generation
```
You are an expert Python developer. Modify this code:

ORIGINAL CODE:
```python
{original_code}
```

INSTRUCTIONS: {change_instructions}

CONTEXT: {additional_context}

Provide complete modified code with:
- Type hints
- Docstrings
- Error handling
- Pythonic style
- Comments for major changes

MODIFIED CODE:
```python
```

## ⚙️ Configuration

### Lightning AI Models
```python
MODELS = {
    "CODE_LLAMA_34B": {
        "name": "codellama/CodeLlama-34b-Instruct-hf",
        "best_for": "code integration, refactoring",
        "speed": "medium",
        "quality": "high"
    },
    "DEEPSEEK_CODER_33B": {
        "name": "deepseek-ai/deepseek-coder-33b-instruct",
        "best_for": "complex refactoring, algorithms",
        "speed": "medium",
        "quality": "very high"
    },
    "STARCODER2_15B": {
        "name": "bigcode/starcoder2-15b",
        "best_for": "quick analysis, simple tasks",
        "speed": "fast",
        "quality": "good"
    }
}
```

### Rate Limiting
```python
RATE_LIMITS = {
    "lightning_ai": {
        "free_tier": 20,  # calls per month
        "pro_tier": 200
    },
    "analysis_cache_ttl": 86400,  # 24 hours
    "max_file_size": 1048576,  # 1MB
    "max_files_per_analysis": 10
}
```

## 📊 Success Metrics

### MVP Success Criteria
- [ ] Successfully analyze 5 different repositories
- [ ] Average analysis time < 60 seconds
- [ ] 80%+ accuracy in identifying relevant files
- [ ] 0 crashes during demo
- [ ] Responsive and clear UI

### Long-term KPIs
- Average integration time: < 15 minutes
- User satisfaction: > 4/5
- Integration success rate: > 90%
- Quota usage efficiency: < 3 calls per integration

## 🧪 Test Cases

### TC-001: Happy Path
```
Given: Valid public GitHub repo URL
When: User submits for analysis
Then: 
  - System clones repo successfully
  - Identifies 3-5 relevant files
  - Shows confidence scores
  - Displays clear integration plan
```

### TC-002: Invalid Input
```
Given: Invalid URL (not GitHub)
When: User submits
Then:
  - Show clear error message
  - Don't consume Lightning AI quota
  - Suggest correct format
```

### TC-003: Large Repository
```
Given: Repo with 100+ files
When: User submits
Then:
  - Analyze only relevant files
  - Complete within 90 seconds
  - Don't timeout
```

### TC-004: Quota Exceeded
```
Given: User has 0 quota remaining
When: User tries to analyze
Then:
  - Disable submit button
  - Show upgrade message
  - Optionally fallback to OpenAI
```

## 🔐 Security Considerations

1. **API Keys**: Never commit to git, use .env
2. **Input Validation**: Sanitize all URLs and file paths
3. **Code Execution**: Never exec() user code
4. **File System**: Sandbox all file operations
5. **Rate Limiting**: Prevent abuse of Lightning AI quota
6. **Dependencies**: Regular security audits

## 📝 Implementation Checklist

### Phase 1: MVP (Week 1-2)
- [ ] Setup project structure
- [ ] Lightning AI integration
- [ ] Basic Reflex UI
- [ ] Git clone functionality
- [ ] Simple analysis prompt
- [ ] Display results
- [ ] Manual testing with 3 repos

### Phase 2: Core Features (Week 3-4)
- [ ] File selection UI
- [ ] Code modification logic
- [ ] Diff generation
- [ ] Backup mechanism
- [ ] Error handling
- [ ] Progress indicators
- [ ] Quota management

### Phase 3: Polish (Week 5-6)
- [ ] Caching layer
- [ ] Multiple model support
- [ ] Better prompts
- [ ] UI improvements
- [ ] Documentation
- [ ] Unit tests
- [ ] Integration tests

### Phase 4: Advanced (Future)
- [ ] Git integration (branches/PRs)
- [ ] VSCode extension
- [ ] CLI tool
- [ ] Collaborative features
- [ ] Analytics dashboard

## 🤝 Contributing Guidelines

### Code Style
- Python: Black formatter, type hints required
- Docstrings: Google style
- Max line length: 88 characters
- Use async/await for I/O operations

### Commit Messages
```
<type>(<scope>): <subject>

<body>

<footer>
```
Types: feat, fix, docs, style, refactor, test, chore

### Pull Request Template
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Manual testing completed
- [ ] No quota wasted

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
```

## 📚 Resources

- Lightning AI Docs: https://lightning.ai/docs
- Reflex Documentation: https://reflex.dev/docs
- LangGraph Guide: https://python.langchain.com/docs/langgraph
- Agent Cookiecutter: https://github.com/neural-maze/agent-api-cookiecutter

---

**Version**: 1.0.0  
**Last Updated**: 2024-03-11 
**Maintainer**: [Amitrobotic]  
**Status**: 🚧 In Development