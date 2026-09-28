# AI Email Automation Agent

An experimental **AI-powered email automation agent** that I built using **n8n** to explore how LLMs can be used to understand, classify, and automate actions around incoming emails.

This project is currently a **working prototype**. My goal with this build was not to create a fully production-ready email platform, but to design and implement the core architecture of an intelligent email workflow and understand the engineering challenges involved in making AI-driven automation reliable.

---

## Why I Built This

Email is one of those tasks that looks simple until you have to deal with a large volume of it.

Every email potentially requires a different action:

* Some need an immediate response.
* Some contain tasks or deadlines.
* Some are meeting requests.
* Some are newsletters.
* Some are spam.
* Some only need to be read and ignored.

I wanted to experiment with whether an AI model could handle the **first layer of decision-making** for me.

Instead of treating an LLM as simply a chatbot that generates text, I wanted to use it as part of an actual automation pipeline:

```text
Email
  ↓
Understand
  ↓
Classify
  ↓
Decide
  ↓
Route
  ↓
Take Action
```

That became the foundation for this project.

---

# What I Built

The system is an **n8n-based email processing workflow**.

It retrieves incoming emails, cleans and structures their contents, sends the relevant information to an LLM for analysis, and then uses the resulting classification to determine what should happen next.

At a high level:

```text
                    ┌─────────────────┐
                    │   Email Inbox   │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  Fetch Emails   │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Normalize Email │
                    │   & Clean Data  │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   AI Analysis   │
                    │                 │
                    │ Intent          │
                    │ Urgency         │
                    │ Sentiment       │
                    │ Entities        │
                    │ Action          │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Intent Router   │
                    └────────┬────────┘
                             │
             ┌───────────────┼────────────────┐
             ▼               ▼                ▼
          Urgent        Action Required     Meeting
             │               │                │
             ▼               ▼                ▼
           Slack          Notion          Date/Time
           Alert           Task            Extraction

             ┌───────────────┼────────────────┐
             ▼               ▼
        Newsletter          Spam
             │               │
             ▼               ▼
          Archive          Quarantine
```

The important part of the project is the combination of **AI reasoning and deterministic workflow automation**.

The AI decides what an email appears to be.

The workflow decides what to do with that result.

---

# Current Features

## 📥 Email Ingestion

The workflow retrieves emails through IMAP and processes them in batches.

The email information is then converted into a structure that the rest of the workflow can work with.

The data includes things such as:

* Sender
* Recipients
* Subject
* Date
* Message ID
* Email content
* HTML content
* Attachment information

---

## 🔄 Duplicate Detection

I added duplicate detection so that the same email does not unnecessarily pass through the AI processing pipeline multiple times.

The current prototype uses n8n workflow data for this mechanism.

This is an area I intend to improve as the system evolves.

---

## 🧹 Email Normalization

Emails are not always received in a clean format.

Some contain HTML, some contain plain text, and others contain additional metadata or formatting.

The workflow therefore normalizes the incoming information before sending it to the AI layer.

This makes the classification step more predictable.

---

# 🧠 AI Email Analysis

The core of the project is the AI classification step.

For every processed email, the model is asked to analyze the message and produce structured information rather than simply returning a natural-language response.

The current analysis includes:

```text
Intent
Confidence
Urgency Score
Sentiment
Entities
Suggested Action
Summary
```

The email can be classified into categories such as:

```text
urgent
action_required
informational
newsletter
spam
meeting_request
```

The system also attempts to identify useful information such as:

* Deadlines
* Action items
* People mentioned
* Projects
* Important dates

This structured output is then passed into the rest of the n8n workflow.

---

# ⚡ Automated Routing

Once an email has been classified, the workflow determines what should happen next.

### Urgent Emails

Urgent messages can trigger a Slack notification.

The idea is that important messages should not have to wait for someone to manually discover them inside an inbox.

### Action-Required Emails

Emails that require action can be converted into tasks through Notion.

The system can also generate a suggested response.

### Meeting Requests

The prototype attempts to identify dates and times contained within meeting-related emails.

This is currently an early implementation rather than a complete calendar automation system.

### Newsletters

Newsletter-type emails can be routed toward a dedicated mailbox folder.

### Spam

Emails classified as spam can be moved toward a spam/quarantine workflow.

---

# ✍️ AI Response Drafting

For emails that require a response, I added a separate AI step that generates a **draft response**.

The system can use information such as:

* The original email
* Detected action items
* Email intent
* Desired response tone

to generate a suggested reply.

Importantly, the current prototype **does not automatically send the generated response**.

I intentionally kept this as a draft-generation step because automatically sending an AI-generated email introduces a completely different level of risk.

A future version could introduce a proper human-approval step before sending anything externally.

---

# 🗓️ Meeting Detection

The prototype also contains an early attempt at extracting meeting-related dates and times from emails.

The current implementation focuses on identifying potential scheduling information.

It does **not yet create calendar events automatically**.

This is one of the areas I would expand in a future iteration.

---

# 🛠️ Technology Stack

| Technology     | Purpose                                     |
| -------------- | ------------------------------------------- |
| **n8n**        | Workflow automation and orchestration       |
| **LLM**        | Email understanding and classification      |
| **IMAP**       | Email retrieval                             |
| **Slack**      | Urgent notifications                        |
| **Notion**     | Task creation                               |
| **PostgreSQL** | Planned persistent application data         |
| **Redis**      | Planned caching / queue infrastructure      |
| **Qdrant**     | Planned vector/RAG infrastructure           |
| **Docker**     | Local infrastructure and service management |
| **JavaScript** | Custom logic inside n8n Code nodes          |

---

# 📁 Project Structure

```text
n8n-built-email-automation-agent-build/
│
├── database/
│   └── schema.sql
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DEPLOYMENT.md
│   └── PROMPTS.md
│
├── monitoring/
│   ├── prometheus.yml
│   └── grafana-dashboard.json
│
├── n8n-workflows/
│   └── email_agent_workflow.json
│
├── .env.example
├── .gitignore
├── docker-compose.yml
├── deploy.bat
├── test.bat
└── README.md
```

---

# 🚧 Prototype Status

This project is intentionally **not presented as a finished production system**.

I built the prototype to establish the core workflow and experiment with the architecture.

There are several areas where the repository contains infrastructure or design ideas that are not yet fully integrated into the main workflow.

For example:

* Deduplication currently relies on n8n workflow data.
* Database persistence is not yet used for every processing event.
* Meeting detection does not yet create calendar events.
* AI responses are generated as drafts rather than automatically sent.
* A complete human-approval system is still to be implemented.
* Qdrant is part of the planned architecture but a complete RAG pipeline is not yet implemented.
* Monitoring infrastructure exists as part of the project direction, but the system is not yet fully instrumented.
* Error handling and recovery need further hardening.

I consider these **next engineering steps**, rather than pretending they are already solved.

---

# What I Learned From Building It

The most interesting part of this project was realizing that an AI automation system is much more complicated than simply connecting an LLM to an API.

Getting an AI model to classify an email is relatively straightforward.

The difficult questions start afterwards:

* What happens when the model is wrong?
* What happens when confidence is low?
* How should duplicate emails be handled?
* Which actions should require approval?
* How can an AI-generated response be safely reviewed?
* What happens when an external API fails?
* How should decisions be logged?
* How can the system be evaluated objectively?
* How should sensitive email information be handled?

These are the problems I want to explore as I continue developing the project.

---

# Future Development

My planned improvements include:

### AI

* Better structured output validation
* Improved classification prompts
* Confidence-based decision making
* Evaluation datasets
* Conversation/thread awareness
* Better handling of attachments
* Context-aware response generation

### Automation

* Human approval before consequential actions
* Automatic calendar integration
* Automated follow-ups
* More advanced Slack workflows
* Better task management integration

### Infrastructure

* Persistent Redis-based processing
* PostgreSQL-backed execution history
* Qdrant-based RAG
* Better retry mechanisms
* Dead-letter queues
* Improved observability
* Prometheus/Grafana monitoring

### Security

* Stronger credential management
* Better protection of email data
* Permission boundaries for automated actions
* Audit logging
* Safer handling of AI-generated content

---

# Running the Project

## Requirements

You will need:

* Docker Desktop
* An IMAP-enabled email account
* An LLM API credential
* Slack credentials if Slack notifications are being used
* Notion credentials if Notion tasks are being used

Start the infrastructure with:

```bash
docker compose up -d
```

Then access n8n at:

```text
http://localhost:5678
```

Import:

```text
n8n-workflows/email_agent_workflow.json
```

Configure the required credentials inside n8n and test the workflow using a controlled mailbox before connecting it to an important email account.

---

# Project Philosophy

I built this project around a simple idea:

> **AI should make workflows more intelligent, not make workflows less predictable.**

The LLM is useful for understanding unstructured human communication.

The workflow automation layer is useful for executing predictable actions.

Combining the two creates something more interesting than either component by itself.

The current implementation is only the beginning.

---

# Current Progress

```text
[x] Email ingestion
[x] Email normalization
[x] Duplicate detection
[x] AI email classification
[x] Intent-based routing
[x] Urgent email notification
[x] Notion task creation
[x] AI response drafting
[x] Newsletter routing
[x] Spam routing
[x] Basic meeting information extraction

[ ] Human approval workflow
[ ] Calendar integration
[ ] Persistent execution history
[ ] Robust retry / recovery system
[ ] RAG implementation
[ ] Automated evaluation
[ ] Production security hardening
[ ] Full observability
[ ] Multi-user support
```

---

# Final Thoughts

This is a **prototype that I built to explore AI-driven workflow automation**.

It is not intended to claim that autonomous email management has been completely solved.

Instead, the project represents my attempt to take an LLM beyond a simple chat interface and place it inside a real automation pipeline where its output can influence actual software behavior.

There is still a lot of engineering work between this prototype and a production-grade system.

That gap is also what makes the project interesting to me.

**This repository is where that experimentation starts.**
