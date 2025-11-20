# 🤖 GitHub Automation Agent

An autonomous GitHub automation system that triggers on push events to perform intelligent code review, automatic README updates, and project progress documentation.

## ✨ Features

### 1. 🔍 Automated Code Review
- **Intelligent Analysis**: Uses LLM (GPT-4 or Claude) to analyze code changes
- **Comprehensive Feedback**: Covers code quality, bugs, security, performance, and best practices
- **Flexible Output**: Post as commit comments or GitHub issues
- **Structured Reviews**: Organized sections for strengths, issues, suggestions, and security concerns

### 2. 📝 Automatic README Updates
- **Smart Detection**: Identifies new functions, classes, API changes, and dependency updates
- **Context-Aware**: Analyzes git diffs to understand what changed
- **Preserves Structure**: Maintains existing README format and tone
- **Complete Updates**: Updates relevant sections without removing unrelated content

### 3. 📊 Project Progress Documentation (spec.md)
- **Development Log**: Tracks project evolution with each push
- **Comprehensive Entries**: Includes change summaries, features, architecture decisions, and milestones
- **Historical Context**: Considers recent commit history for better insights
- **Next Steps**: Suggests remaining tasks based on current state

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     GitHub Push Event                        │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Webhook Server (Flask)                    │
│                                                              │
│  • Receives push events                                     │
│  • Verifies HMAC-SHA256 signature                          │
│  • Extracts commit information                              │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   Automation Orchestrator                    │
│                                                              │
│  Coordinates three parallel tasks:                          │
└───────────┬─────────────────┬────────────────┬──────────────┘
            │                 │                │
            ↓                 ↓                ↓
    ┌───────────┐     ┌──────────┐    ┌──────────┐
    │   Code    │     │ README   │    │  Spec    │
    │  Review   │     │ Updater  │    │ Updater  │
    └─────┬─────┘     └────┬─────┘    └────┬─────┘
          │                │               │
          ↓                ↓               ↓
    ┌─────────────────────────────────────────┐
    │          LLM Client (OpenAI/Anthropic)  │
    └─────────────────────────────────────────┘
          │                │               │
          ↓                ↓               ↓
    ┌──────────┐     ┌──────────┐    ┌──────────┐
    │ Post     │     │ Create   │    │ Append   │
    │ Comment  │     │ PR/Commit│    │ to spec  │
    └──────────┘     └──────────┘    └──────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- GitHub account with repository access
- GitHub Personal Access Token
- OpenAI API key or Anthropic API key

### Installation

```bash
# Clone repository
git clone https://github.com/Amitro123/GithubAgent.git
cd GithubAgent
git checkout automation-agent-setup

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials
```

### Configuration

Edit `.env`:

```bash
GITHUB_TOKEN=ghp_your_token_here
GITHUB_WEBHOOK_SECRET=your_secret_here
REPOSITORY_OWNER=your_username
REPOSITORY_NAME=your_repo

LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your_key_here

CREATE_PR=True
AUTO_COMMIT=False
POST_REVIEW_AS_ISSUE=False
```

### Run

```bash
python -m automation_agent.main
```

See [SETUP.md](SETUP.md) for detailed setup instructions.

## 📋 Workflow

1. **Developer pushes code** → GitHub webhook triggers
2. **Webhook server receives event** → Verifies signature, extracts commit data
3. **Orchestrator executes tasks**:
   - **Code Review**: Analyzes diff, generates review, posts comment/issue
   - **README Update**: Detects changes, updates documentation, creates PR
   - **Spec Update**: Documents progress, appends to spec.md
4. **Results posted** → PR created or files committed

## 🔒 Security

- **Webhook Signature Verification**: HMAC-SHA256 validation prevents unauthorized requests
- **Environment Variables**: Sensitive credentials stored securely
- **Token Permissions**: Minimal required GitHub permissions
- **HTTPS Required**: Webhook endpoint must use HTTPS in production

## ⚙️ Configuration Options

### Automation Behavior

| Option | Description | Default |
|--------|-------------|---------|
| `CREATE_PR` | Create PRs for documentation updates | `True` |
| `AUTO_COMMIT` | Directly commit to branch (use with caution) | `False` |
| `POST_REVIEW_AS_ISSUE` | Post reviews as issues instead of comments | `False` |

### LLM Configuration

| Option | Description | Example |
|--------|-------------|---------|
| `LLM_PROVIDER` | LLM provider to use | `openai` or `anthropic` |
| `LLM_MODEL` | Model name | `gpt-4-turbo-preview` |
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` |
| `ANTHROPIC_API_KEY` | Anthropic API key | `sk-ant-...` |

## 📦 Project Structure

```
automation_agent/
├── __init__.py              # Package initialization
├── config.py                # Configuration management
├── github_client.py         # GitHub API wrapper
├── llm_client.py           # LLM client (OpenAI/Anthropic)
├── code_reviewer.py        # Code review module
├── readme_updater.py       # README update module
├── spec_updater.py         # Spec documentation module
├── orchestrator.py         # Task coordination
├── webhook_server.py       # Flask webhook server
└── main.py                 # Entry point

requirements.txt            # Python dependencies
.env.example               # Environment template
SETUP.md                   # Setup instructions
```

## 🧪 Testing

### Health Check
```bash
curl http://localhost:8080/
```

### Test Push Event
```bash
echo "# Test" >> test.txt
git add test.txt
git commit -m "test: trigger automation"
git push
```

### Expected Results
1. ✅ Code review posted as commit comment or issue
2. ✅ PR created with README updates (if changes detected)
3. ✅ spec.md updated with progress entry

## 🌐 Deployment

### Local Development
Use ngrok or localtunnel for testing:
```bash
ngrok http 8080
```

### Production Options
- **Cloud VM**: AWS EC2, DigitalOcean, Google Cloud
- **Docker**: Containerized deployment
- **Serverless**: AWS Lambda + API Gateway
- **Platform**: Heroku, Railway, Render

See [SETUP.md](SETUP.md) for detailed deployment instructions.

## 🔧 Troubleshooting

### Common Issues

**Webhook Signature Verification Failed**
- Verify `GITHUB_WEBHOOK_SECRET` matches webhook configuration

**LLM API Errors**
- Check API key validity and quota
- Test with smaller diffs
- Switch LLM provider if needed

**Files Not Updated**
- Verify `CREATE_PR` or `AUTO_COMMIT` is enabled
- Check GitHub token permissions
- Review logs for errors

**Webhook Not Receiving Events**
- Ensure webhook URL is publicly accessible
- Check webhook deliveries on GitHub
- Verify server is running

## 📚 Documentation

- **[SETUP.md](SETUP.md)**: Complete setup and deployment guide
- **[.env.example](.env.example)**: Configuration template
- **Code Comments**: Inline documentation in source files

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- OpenAI and Anthropic for LLM APIs
- GitHub for webhook infrastructure
- Flask for web framework

---

**Built with ❤️ for automated code quality and documentation**
