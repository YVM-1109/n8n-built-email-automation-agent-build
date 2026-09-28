# Deployment Guide

## Prerequisites

- Windows 10/11 (64-bit)
- Docker Desktop installed and running
- 4 GB RAM minimum (8 GB recommended)
- 10 GB free disk space
- Internet connection

## Quick Start

### Option 1: One-Click Deploy (Windows CMD)

```cmd
# 1. Clone or extract this repository
cd email-agent

# 2. Run the deploy script
deploy.bat

# 3. Enter your API keys when prompted
#    - OpenAI API Key
#    - Gmail address + App Password
#    - Slack Bot Token (optional)
#    - Notion API Key (optional)
```

### Option 2: Manual Deploy

```cmd
# 1. Copy environment template
copy .env.example .env

# 2. Edit .env with your credentials
notepad .env

# 3. Start services
docker compose up -d

# 4. Initialize database
docker cp database/schema.sql email-agent-postgres:/schema.sql
docker exec -i email-agent-postgres psql -U n8n -d n8n -f /schema.sql

# 5. Open n8n
start http://localhost:5678
```

## Post-Deployment Setup

### 1. Import Workflow

1. Open http://localhost:5678
2. Sign in with credentials from `.env` (default: admin / change_me_now)
3. **Workflows** → **Import from File** → Select `n8n-workflows/email_agent_workflow.json`

### 2. Add Credentials

Go to **Settings** → **Credentials** → **Add Credential**:

| Service | Type | Required Values |
|---------|------|-----------------|
| Gmail | IMAP Account | Host: imap.gmail.com, Port: 993, User: your@gmail.com, Password: app password, SSL: ON |
| OpenAI | OpenAI API | API Key: your key |
| Slack | Slack API | Access Token: xoxb-your-token |
| Notion | Notion API | API Key: secret_your_key |

**Important:** After creating credentials, open each node in the workflow and select the credential from the dropdown.

### 3. Activate

1. Click **Save** (Ctrl+S)
2. Click **Activate** toggle (top-right)
3. The workflow polls Gmail every 60 seconds

## Verification

Run the test script:

```cmd
test.bat
```

Or manually check:

```cmd
# Check services
docker compose ps

# Check database
docker exec -i email-agent-postgres psql -U n8n -d n8n -c "SELECT * FROM emails ORDER BY created_at DESC LIMIT 5;"

# Check Redis
docker exec -i email-agent-redis redis-cli ping

# Check Qdrant
curl http://localhost:6333/healthz
```

## Daily Operations

| Task | Command |
|------|---------|
| Start | `docker compose up -d` |
| Stop | `docker compose down` |
| Restart | `docker compose restart` |
| View logs | `docker compose logs -f n8n` |
| Backup DB | `docker exec email-agent-postgres pg_dump -U n8n n8n > backup.sql` |
| Restore DB | `docker exec -i email-agent-postgres psql -U n8n -d n8n < backup.sql` |
| Update | `docker compose pull && docker compose up -d` |
| Reset all data | `docker compose down -v` ⚠️ Deletes everything |

## Troubleshooting

### "Docker is not installed"
Install Docker Desktop: https://www.docker.com/products/docker-desktop

### "Port 5432 already in use"
Stop local PostgreSQL: `net stop postgresql-x64-15`

### "IMAP connection failed"
- Enable 2-Factor Authentication on Gmail
- Generate App Password at myaccount.google.com/apppasswords
- Use the 16-character app password, NOT your regular password

### "OpenAI API error"
- Verify key at platform.openai.com
- Check available credits
- The workflow uses GPT-4o-mini (~$0.15 per 1K emails)

### "Credential not found"
- Create credentials in n8n Settings, not just in .env
- Open each workflow node and select credential from dropdown

### n8n won't start
```cmd
docker compose down
docker compose up -d
docker compose logs n8n
```
