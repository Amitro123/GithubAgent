# GitHub Automation Agent - Setup Guide

Complete setup instructions for the autonomous GitHub automation agent that performs code review, README updates, and project documentation on every push.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [GitHub Webhook Setup](#github-webhook-setup)
5. [Running the Agent](#running-the-agent)
6. [Deployment Options](#deployment-options)
7. [Testing](#testing)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- **Python 3.9+**
- **GitHub Account** with repository access
- **GitHub Personal Access Token** with appropriate permissions
- **LLM API Key** (OpenAI or Anthropic)
- **Public URL** for webhook endpoint (for production use)

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/Amitro123/GithubAgent.git
cd GithubAgent
git checkout automation-agent-setup
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Configuration

### 1. Create Environment File

Copy the example environment file:

```bash
cp .env.example .env
```

### 2. Configure Environment Variables

Edit `.env` and fill in your credentials:

```bash
# GitHub Configuration
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GITHUB_WEBHOOK_SECRET=your_random_secret_string_here
REPOSITORY_OWNER=Amitro123
REPOSITORY_NAME=GithubAgent

# LLM Configuration
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
LLM_MODEL=gpt-4-turbo-preview

# Server Configuration
HOST=0.0.0.0
PORT=8080
DEBUG=False

# Automation Behavior
CREATE_PR=True
AUTO_COMMIT=False
POST_REVIEW_AS_ISSUE=False
```

### 3. GitHub Personal Access Token

Create a token at: https://github.com/settings/tokens

**Required Permissions:**
- `repo` (Full control of private repositories)
- `write:discussion` (if posting reviews as issues)

### 4. Webhook Secret

Generate a secure random string for webhook verification:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Use this value for `GITHUB_WEBHOOK_SECRET`.

---

## GitHub Webhook Setup

### 1. Expose Your Server

For local development, use a tunneling service:

**Option A: ngrok**
```bash
ngrok http 8080
```

**Option B: localtunnel**
```bash
npx localtunnel --port 8080
```

Copy the public URL (e.g., `https://abcd1234.ngrok.io`).

### 2. Configure Webhook on GitHub

1. Go to your repository on GitHub
2. Navigate to **Settings** → **Webhooks** → **Add webhook**
3. Configure:
   - **Payload URL**: `https://your-public-url.com/webhook`
   - **Content type**: `application/json`
   - **Secret**: Your `GITHUB_WEBHOOK_SECRET` value
   - **Events**: Select "Just the push event"
   - **Active**: ✓ Checked
4. Click **Add webhook**

### 3. Verify Webhook

GitHub will send a ping event. Check:
- Webhook shows a green checkmark
- Recent deliveries show successful responses

---

## Running the Agent

### Development Mode

```bash
cd automation_agent
python -m automation_agent.main
```

Or:

```bash
python -m automation_agent.main
```

The server will start on `http://0.0.0.0:8080`.

### Production Mode (with Gunicorn)

```bash
gunicorn -w 4 -b 0.0.0.0:8080 automation_agent.webhook_server:app
```

For production, use:
- Multiple workers (`-w 4`)
- Proper logging configuration
- Process manager (systemd, supervisor)

---

## Deployment Options

### Option 1: Local Development

Use ngrok/localtunnel for testing:

```bash
# Terminal 1: Start the agent
python -m automation_agent.main

# Terminal 2: Expose with ngrok
ngrok http 8080
```

### Option 2: Cloud VM (AWS EC2, DigitalOcean, etc.)

1. **Launch a VM** (Ubuntu 22.04 recommended)
2. **Install dependencies**:
   ```bash
   sudo apt update
   sudo apt install python3-pip python3-venv
   ```
3. **Clone and setup** (follow installation steps)
4. **Configure firewall**:
   ```bash
   sudo ufw allow 8080/tcp
   ```
5. **Run with systemd**:

Create `/etc/systemd/system/github-automation.service`:

```ini
[Unit]
Description=GitHub Automation Agent
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/GithubAgent
Environment="PATH=/home/ubuntu/GithubAgent/venv/bin"
ExecStart=/home/ubuntu/GithubAgent/venv/bin/python -m automation_agent.main
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable github-automation
sudo systemctl start github-automation
sudo systemctl status github-automation
```

### Option 3: Docker Container

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY automation_agent/ ./automation_agent/
COPY .env .

EXPOSE 8080

CMD ["python", "-m", "automation_agent.main"]
```

Build and run:
```bash
docker build -t github-automation-agent .
docker run -d -p 8080:8080 --env-file .env github-automation-agent
```

### Option 4: Serverless (AWS Lambda + API Gateway)

1. Package the application with dependencies
2. Create Lambda function with API Gateway trigger
3. Configure environment variables in Lambda
4. Use API Gateway URL as webhook endpoint

---

## Testing

### 1. Health Check

```bash
curl http://localhost:8080/
```

Expected response:
```json
{
  "status": "healthy",
  "service": "GitHub Automation Agent",
  "version": "1.0.0"
}
```

### 2. Test Push Event

Make a commit and push to your repository:

```bash
echo "# Test" >> test.txt
git add test.txt
git commit -m "test: trigger automation"
git push
```

### 3. Verify Automation

Check for:
1. **Code Review**: Commit comment or GitHub issue created
2. **README Update**: PR created or file updated (if changes detected)
3. **Spec Update**: spec.md updated with progress entry

### 4. Check Logs

```bash
# If running directly
# Logs appear in terminal

# If using systemd
sudo journalctl -u github-automation -f

# If using Docker
docker logs -f <container-id>
```

---

## Troubleshooting

### Webhook Signature Verification Failed

**Symptom**: 403 Forbidden responses

**Solution**:
- Verify `GITHUB_WEBHOOK_SECRET` matches webhook configuration
- Check webhook secret is properly set on GitHub

### LLM API Errors

**Symptom**: Code review/updates failing

**Solution**:
- Verify API key is correct and active
- Check API quota/rate limits
- Test with smaller diffs
- Switch LLM provider if needed

### GitHub API Rate Limits

**Symptom**: 403 responses from GitHub API

**Solution**:
- Use authenticated requests (token should be set)
- Implement exponential backoff (already included)
- Reduce automation frequency

### Files Not Updated

**Symptom**: No PRs or commits created

**Solution**:
- Check `CREATE_PR` and `AUTO_COMMIT` settings
- Verify GitHub token has write permissions
- Check logs for errors

### Webhook Not Receiving Events

**Symptom**: No logs when pushing

**Solution**:
- Verify webhook URL is accessible publicly
- Check webhook deliveries on GitHub (Settings → Webhooks)
- Ensure server is running
- Check firewall rules

---

## Configuration Options Explained

### Automation Behavior

**CREATE_PR=True** (Recommended)
- Creates pull requests for documentation updates
- Allows review before merging
- Safer for production

**AUTO_COMMIT=True** (Use with caution)
- Directly commits to the branch
- No manual review required
- Faster but riskier

**POST_REVIEW_AS_ISSUE=True**
- Posts code reviews as GitHub issues
- Better visibility and discussion
- Alternative to commit comments

---

## Architecture Overview

```
Push Event → GitHub Webhook → Webhook Server
                                    ↓
                          Signature Verification
                                    ↓
                            Orchestrator
                    ┌───────────┼───────────┐
                    ↓           ↓           ↓
              Code Review   README Update  Spec Update
                    ↓           ↓           ↓
              LLM Analysis  LLM Generation LLM Generation
                    ↓           ↓           ↓
              Post Comment   Create PR    Append to spec.md
```

---

## Security Best Practices

1. **Never commit `.env`** to version control
2. **Use strong webhook secrets** (32+ random characters)
3. **Rotate API keys** regularly
4. **Limit token permissions** to minimum required
5. **Use HTTPS** for webhook endpoints
6. **Monitor webhook deliveries** for suspicious activity
7. **Implement rate limiting** if exposing publicly

---

## Next Steps

1. ✅ Complete setup and test locally
2. ✅ Deploy to production environment
3. ✅ Monitor first few automation runs
4. ✅ Fine-tune prompts if needed
5. ✅ Add custom automation rules
6. ✅ Integrate with CI/CD pipeline

---

## Support & Contributing

- **Issues**: https://github.com/Amitro123/GithubAgent/issues
- **Documentation**: See README.md
- **Contributing**: Pull requests welcome!

---

**Happy Automating! 🤖**
