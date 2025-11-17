# GithubAgent - Repo Refactor AI Agent

AI-powered repository refactoring and integration tool using Lightning AI and Gemini.

## Overview

GithubAgent analyzes a GitHub repository, plans the integration into your existing
project, and applies the required code changes automatically. It uses a
**multi-agent orchestration** flow:

- Analysis Agent (Lightning AI)
- Implementation Agent
- Research Agent (Gemini + grounded search + StudioAI logs)
- Diff Agent
- (planned) Summary / Testing / Finalization agents

The goal is to reduce integration time from days/hours to **10–15 minutes**.

## Architecture

### High-Level Flow

1. **Analysis Phase**
   - Input: repository contents + user instructions.
   - Agent: `CodeAnalysisAgent`.
   - Output: `AnalysisResult` (files, dependencies, risks, steps).

2. **Implementation Phase**
   - Input: `AnalysisResult` + original repo.
   - Agent: `ImplementationAgent` (Lightning AI backend).
   - Output: `ImplementationResult` (modified files, errors, logs).

3. **Research + Retry Phase (on failure)**
   - Trigger: `ImplementationResult.success == False`.
   - Agent: `ResearchAgent` (Gemini).
   - Uses:
     - error message,
     - (optional) failing code snippet,
     - **StudioAI / execution logs** from the implementation step.
   - Output: `ResearchResult` (solutions, recommendations, search queries).
   - Orchestrator appends recommendations and best code snippet to the
     implementation instructions and retries the Implementation Agent.

4. **Diff Phase**
   - Agent: `DiffAgent`.
   - Generates a human-readable diff of all changes.

5. **(Future) Summary / Testing / Finalization**
   - Summary Agent: human-readable summary of changes.
   - Testing Agent: run tests/linters.
   - Finalization Agent: finalize or roll back.

### Key Modules

- `src/repofactor/domain/models/integration_models.py`
  - `AnalysisResult`, `AffectedFile`, `ImplementationResult`, `OrchestratorState`,
    `Solution`, `ResearchResult`.
- `src/repofactor/application/agent_service/multi_agent_orchestrator.py`
  - Multi-agent flow controller.
- `src/repofactor/application/agent_service/agent_orchestrator_decision.py`
  - Pure decision logic for next agent (`orchestrator_decide_next`).
- `src/repofactor/application/agent_service/research_agent.py`
  - Gemini-based Research Agent integration.
- `src/repofactor/infrastructure/utils/code_parser.py`
  - AST-based code parser and Gemini grounding parsers.
- `src/repofactor/domain/prompts/prompt_research_agnet.py`
  - Prompt builder and recommendation generator for the Research Agent.

For a full product specification, see `agentcore/SPEC.md`.

## Setup

### Requirements

- Python 3.11+ (tested with 3.12)
- `pip` or `poetry`

Install dependencies:

```bash
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the project root (or set env vars directly):

```bash
cp .env.example .env
```

Required variables:

- `LIGHTNING_API_KEY`  
  Used by `LightningAIClient` for Analysis and Implementation agents.

- `GEMINI_API_KEY`  
  Used by `ResearchAgent` (Gemini) for grounded web research.

Optional variables:

- `MOCK_LIGHTNING_AI=true` – use mock responses during local development.
- `LOG_LEVEL=INFO` or `DEBUG` for richer logs.

## Research Agent Integration

The Research Agent is integrated into the orchestrator via:

- `OrchestratorState` (in `integration_models.py`)
  - `current_stage`
  - `retry_count`
  - `last_error_message`

- `agent_orchestrator_decision.py`
  - When `current_stage == "implementation_failed"` and `retry_count < 3`:
    - returns `"research_agent"`.
  - Otherwise returns `"report_failure"`.

- `multi_agent_orchestrator.py`
  - On implementation failure:
    - stores the error in `state.last_error_message`.
  - On `"research_agent"` step:
    - builds context including:
      - `repo`
      - `user_instructions`
      - StudioAI / execution logs (`execution_logs`).
    - calls `ResearchAgent.best_fix_snippet(...)`.
    - appends the best snippet (if present) to `self.instructions` as
      `# Suggested fix from research`.
    - sets `current_stage = "implementation_retry"`.
  - On `"implementation_retry"`:
    - re-runs the Implementation Agent with updated instructions.
    - updates `retry_count` and `last_error_message` accordingly.

### Gemini Grounding & StudioAI Logs

- Grounding:
  - `ResearchAgent` uses `google.generativeai` with
    `tools="google_search_retrieval"`.
  - Results are parsed via `parse_grounded_response` to `Solution` objects.
  - `extract_search_queries` recovers queries from the Gemini output.

- StudioAI / execution logs:
  - Collected inside `ImplementationResult.execution_logs`.
  - Passed via `context["studio_logs"]` into `build_research_prompt`.
  - Prompt includes the last lines of logs to give Gemini execution context.

## How to Run the Orchestrator

From the project root (`GithubAgent`):

### 1. Run tests / E2E flow

```bash
pytest agentcore/tests
```

See `agentcore/tests/test_e2e_localy.py` for the end-to-end test harness.

### 2. Run the orchestration flow programmatically

You can use the example in `multi_agent_orchestrator.py`:

```bash
python -m repofactor.application.agent_service.multi_agent_orchestrator
```

This runs `example_run()` with a simple in-memory repo.

### 3. Use the CLI for Decision Logic

From the project root:

```bash
python -m repofactor.application.orchestrator_cli \
  --approval_received \
  --current_stage analysis_complete
```

This uses `OrchestratorState` plus `orchestrator_decide_next` to print the
next agent.

## Token Efficiency

- Uses TOON format for 30–60% fewer tokens (see `agentcore/SPEC.md`).
- Automatic fallback to JSON if TOON fails.
- Smart file truncation for long source files.

## Contributing

See `agentcore/SPEC.md` and `CONTRIBUTING.md` (if present) for guidelines.

## Changelog

- v0.1.0:
  - Added multi-agent orchestrator with Research Agent integration.
  - Implemented Gemini grounding + StudioAI log usage.
  - Updated data models and README.
- v0.0.1:
  - Updated spec.md.
- v0.0.0:
  - Initial release, README.md update.
