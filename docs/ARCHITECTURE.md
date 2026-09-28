# Architecture

## System Overview

The Email Management Agent is a production-grade, agentic AI system that automatically ingests, classifies, and acts on emails using LLM-powered decision-making.

```
┌─────────────────────────────────────────────────────────────┐
│                     INGESTION LAYER                          │
│  Gmail IMAP  │  Outlook Graph  │  Generic IMAP  │ Webhook  │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                  PRE-PROCESSING PIPELINE                     │
│  Deduplication → Content Extraction → Normalization → Queue  │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                   AGENTIC AI CORE                            │
│  LLM Intent Classification → Entity Extraction → Routing     │
│  RAG Knowledge Base → Sentiment Analysis → Fairness Audit    │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                     ACTION LAYER                             │
│  Slack Alerts │ Notion Tasks │ Draft Responses │ Calendar   │
│  Auto-Archive │ Spam Quarantine │ Human Approval Loop      │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                  OBSERVABILITY LAYER                         │
│  PostgreSQL Logs │ Prometheus Metrics │ Grafana Dashboards │
│  Dead Letter Queue │ Error Handling │ Circuit Breaker      │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

1. **Trigger** — IMAP polls Gmail every 60 seconds (or webhook push)
2. **Deduplicate** — Redis-backed Message-ID cache prevents reprocessing
3. **Extract** — HTML → Markdown, attachments → metadata, sender normalization
4. **Classify** — GPT-4o-mini analyzes intent, urgency, sentiment, entities
5. **Route** — Switch node directs to specialized action sub-workflow
6. **Act** — Slack alert, Notion task, draft response, archive, or quarantine
7. **Log** — Every action recorded in PostgreSQL for analytics

## Component Diagram

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Gmail     │     │   Redis     │     │  PostgreSQL │
│   (IMAP)    │◄────┤   (Cache)   │     │   (Logs)    │
└──────┬──────┘     └─────────────┘     └─────────────┘
       │
       │ HTTP
┌──────▼──────┐     ┌─────────────┐     ┌─────────────┐
│     n8n     │────►│   OpenAI    │     │   Qdrant    │
│  (Workflow) │     │  (GPT-4o)   │     │  (Vectors)  │
└──────┬──────┘     └─────────────┘     └─────────────┘
       │
       ├────────────► Slack
       ├────────────► Notion
       └────────────► Gmail (move)
```

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Workflow Engine | n8n (self-hosted) |
| Database | PostgreSQL 15 |
| Cache / Queue | Redis 7 |
| Vector DB | Qdrant |
| LLM | OpenAI GPT-4o / GPT-4o-mini |
| Monitoring | Prometheus + Grafana (optional) |
| Containerization | Docker + Docker Compose |

## Scalability

- **Horizontal:** Add n8n worker containers with `N8N_MODE=worker`
- **Queue Mode:** Enable Redis-backed execution queue for high volume
- **Database:** Partition execution_logs by month for >1M records
- **LLM Cost:** Use GPT-4o-mini for classification (~$0.15/1K emails), GPT-4o only for drafting
