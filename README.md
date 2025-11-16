# GithubAgent

This repository contains the GithubAgent project.

## Changelog

- v0.0.1: Updated spec.md
- v0.0.0: Initial release, README.md update.

# GithubAgent - Repo Refactor AI Agent

## Features
- 🎯 Repository Analysis with TOON format (30-60% token reduction)
- 🤖 Lightning AI integration
- 🔄 Automatic fallback mechanisms
- 📊 Detailed risk assessment

## Quick Start


pip install -r requirements.txt
cp .env.example .env # Add your LIGHTNING_API_KEY
python agentcore/tests/test_e2e_localy.py

## Architecture
- Analysis Agent: Analyzes repos and suggests changes
- [TODO] Modification Agent: Applies changes
- [TODO] Validation Agent: Tests changes
- [TODO] Documentation Agent: Documents changes

## Token Efficiency
- Uses TOON format for 30-60% fewer tokens
- Automatic fallback to JSON if TOON fails
- Smart file truncation (400 chars per file)

## Contributing
See CONTRIBUTING.md
