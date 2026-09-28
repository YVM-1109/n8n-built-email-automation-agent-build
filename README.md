# Email Management Agent

> A production-grade, agentic AI system that automatically ingests, classifies, and acts on emails using LLM-powered decision-making. Built with n8n, OpenAI, PostgreSQL, Redis, and Docker.

[![Docker](https://img.shields.io/badge/Docker-Ready-blue)](https://docker.com)
[![n8n](https://img.shields.io/badge/n8n-Self--hosted-orange)](https://n8n.io)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-green)](https://openai.com)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## Features

- **Intelligent Classification** — GPT-4o-mini analyzes every email for intent, urgency, sentiment, and entities
- **Dynamic Routing** — Automatically routes emails to Slack alerts, Notion tasks, draft responses, calendar extraction, or spam quarantine
- **Deduplication Engine** — Redis-backed cache prevents reprocessing the same email
- **Human-in-the-Loop** — Low-confidence or high-urgency emails pause for approval
- **Real-Time Streaming** — Polls Gmail IMAP every 60 seconds (or webhook push)
- **Analytics & Observability** — Full execution logging in PostgreSQL with Grafana dashboards
- **Fault Tolerance** — Dead letter queue, circuit breaker, exponential backoff retries
- **Zero Cost** — Self-hosted stack; only pay for OpenAI API usage (~$0.50/1K emails)

---

## Architecture

```
Gmail IMAP (every 60s)
    |
    v
[Deduplication] --skip duplicates-->
    |
    v
[Content Extraction] --clean HTML, extract text-->
    |
    v
[LLM Classification] --GPT-4o-mini: intent, urgency, sentiment-->
    |
    v
[Intent Router] --branch by category-->
    |--urgent--------> Slack Alert (#email-alerts)
    |--action_req----> Notion Task + Draft Response (GPT-4o)
    |--meeting-------> Extract Dates → Calendar
    |--newsletter----> Archive to "Newsletters" folder
    |--spam----------> Quarantine to "Spam" folder
    |--default-------> Log to PostgreSQL
```

**Full architecture:** See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop) (Windows/Mac/Linux)
- 4 GB RAM minimum
- OpenAI API key ([get one free](https://platform.openai.com/api-keys))
- Gmail App Password ([generate here](https://myaccount.google.com/apppasswords))

### Deploy (Windows)

```cmd
# 1. Clone or download this repository
cd email-agent

# 2. Run the deploy script
deploy.bat

# 3. Enter your API keys when prompted
```

### Deploy (Linux/Mac)

```bash
cd email-agent
cp .env.example .env
# Edit .env with your credentials
nano .env
docker compose up -d
docker cp database/schema.sql email-agent-postgres:/schema.sql
docker exec -i email-agent-postgres psql -U n8n -d n8n -f /schema.sql
```

### Post-Deployment

1. Open http://localhost:5678
2. Sign in with credentials from `.env` (default: `admin` / `change_me_now`)
3. **Workflows** → **Import from File** → Select `n8n-workflows/email_agent_workflow.json`
4. Add credentials in **Settings** → **Credentials** (IMAP, OpenAI, Slack, Notion)
5. Open each workflow node and select your credential from the dropdown
6. Click **Save** → **Activate**

**Full guide:** See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

---

## Project Structure

```
email-agent/
├── docker-compose.yml          # Infrastructure stack
├── .env.example                # Configuration template
├── deploy.bat                  # One-click Windows deploy
├── test.bat                    # Health check script
├── README.md                   # This file
├── .gitignore                  # Git ignore rules
│
├── n8n-workflows/
│   └── email_agent_workflow.json   # Importable n8n workflow (15 nodes)
│
├── database/
│   └── schema.sql              # PostgreSQL schema (6 tables, 2 views)
│
├── monitoring/
│   ├── prometheus.yml          # Metrics collection config
│   └── grafana-dashboard.json  # Operations dashboard (17 panels)
│
├── docs/
│   ├── ARCHITECTURE.md         # System design & tech stack
│   ├── DEPLOYMENT.md           # Step-by-step deploy guide
│   └── PROMPTS.md              # LLM prompt library (8 prompts)
│
└── scripts/                    # Additional automation scripts
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Workflow Engine | [n8n](https://n8n.io) (self-hosted) |
| LLM | [OpenAI GPT-4o / GPT-4o-mini](https://openai.com) |
| Database | [PostgreSQL 15](https://postgresql.org) |
| Cache / Queue | [Redis 7](https://redis.io) |
| Vector DB | [Qdrant](https://qdrant.tech) |
| Monitoring | [Prometheus](https://prometheus.io) + [Grafana](https://grafana.com) |
| Containerization | [Docker](https://docker.com) + Docker Compose |

---

## Cost Breakdown

| Component | Monthly Cost |
|-----------|-------------|
| Self-hosted n8n | **$0** |
| Docker / PostgreSQL / Redis | **$0** |
| OpenAI GPT-4o-mini | **~$0.50** per 1,000 emails |
| Gmail IMAP | **$0** |
| Slack (free tier) | **$0** |
| Notion (free tier) | **$0** |
| **Total** | **$0–$5/month** |

---

## Screenshots

*(Add screenshots of your n8n workflow, Grafana dashboard, and Slack alerts here)*

---

## API & Integrations

The workflow supports these integrations out of the box:

- **Gmail** (IMAP) — Email ingestion
- **Outlook / Exchange** (Microsoft Graph) — Enterprise email
- **Slack** — Urgent alerts and approvals
- **Notion** — Task creation and tracking
- **OpenAI** — LLM classification and drafting
- **Any webhook** — Custom triggers

---

## Monitoring

Enable Prometheus + Grafana by uncommenting the services in `docker-compose.yml`:

```yaml
  prometheus:
    # ... (uncomment this block)

  grafana:
    # ... (uncomment this block)
```

Then access:
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin / from `.env`)

**Dashboard includes:** Emails processed, error rate, LLM cost, queue depth, latency percentiles, pending approvals.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Docker not found | Install [Docker Desktop](https://docker.com) |
| Port 5432 in use | Stop local PostgreSQL: `net stop postgresql-x64-15` |
| IMAP connection failed | Use Gmail App Password, not regular password |
| OpenAI API error | Check credits at [platform.openai.com](https://platform.openai.com) |
| Credential not found | Create in n8n Settings, then select in each node |
| n8n won't start | `docker compose down && docker compose up -d` |

**Full troubleshooting:** See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

---

## Roadmap

- [ ] Kubernetes Helm chart for cloud deployment
- [ ] RAG knowledge base with Qdrant vector search
- [ ] Multi-user support with role-based access
- [ ] Calendar integration (Google Calendar, Cal.com)
- [ ] Mobile app for approval notifications
- [ ] Advanced spam/phishing detection with local LLM

---

## Contributing

1. Fork this repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -am 'Add new feature'`
4. Push to the branch: `git push origin feature/my-feature`
5. Open a Pull Request

---

## License

This project is licensed under the MIT License.

---

## Acknowledgments

- Built with [n8n](https://n8n.io) — the fair-code workflow automation platform
- LLM powered by [OpenAI](https://openai.com)
- Vector search by [Qdrant](https://qdrant.tech)

---

**Status: Production Ready** ✅

Double-click `deploy.bat` to get started.
