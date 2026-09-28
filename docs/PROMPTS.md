# LLM Prompt Library

All prompts are optimized for OpenAI GPT-4o / GPT-4o-mini.

## 1. Intent Classification
**Model:** GPT-4o-mini | **Temperature:** 0.1 | **Max Tokens:** 500

```
You are an expert email triage agent. Analyze the following email and classify it.

**Email:**
Subject: {subject}
From: {sender_name} <{sender_email}>
Date: {date}
Content: {email_body}

Return ONLY JSON (no markdown, no explanation):
{
  "intent": "urgent|action_required|informational|newsletter|spam|meeting_request",
  "confidence": 0.0-1.0,
  "urgency_score": 1-10,
  "sentiment": "positive|neutral|negative",
  "entities": {
    "deadlines": ["ISO dates"],
    "action_items": ["tasks"],
    "people_mentioned": ["names"],
    "projects": ["tags"]
  },
  "suggested_action": "reply|forward|archive|flag|create_task|schedule_meeting|quarantine",
  "summary": "2-3 sentence summary"
}
```

## 2. Response Drafting
**Model:** GPT-4o | **Temperature:** 0.7 | **Max Tokens:** 1500

```
Draft a professional email response to:

From: {sender_name}
Subject: {subject}
Content: {email_body}

Context:
- Intent: {intent}
- Action Items: {action_items}
- Tone: Professional but warm

Return ONLY the email body text.
```

## 3. Meeting Extraction
**Model:** GPT-4o-mini | **Temperature:** 0.1 | **Max Tokens:** 400

```
Extract meeting information from this email:
Subject: {subject}
Content: {email_body}

Return STRICT JSON:
{
  "is_meeting_request": true|false,
  "confidence": 0.0-1.0,
  "proposed_times": [{"start": "ISO 8601", "end": "ISO 8601"}],
  "meeting_type": "string",
  "duration_minutes": number,
  "location": "string",
  "agenda": ["items"]
}
```

## 4. Spam/Phishing Detection
**Model:** GPT-4o-mini | **Temperature:** 0.05 | **Max Tokens:** 300

```
Detect if this email is spam or phishing:
From: {sender_email}
Subject: {subject}
Links: {extracted_links}
Content: {email_body}

Return STRICT JSON:
{
  "is_spam": true|false,
  "is_phishing": true|false,
  "threat_level": "none|low|medium|high|critical",
  "indicators": ["suspicious elements"],
  "recommended_action": "allow|quarantine|block|report"
}
```

## 5. Weekly Digest
**Model:** GPT-4o | **Temperature:** 0.5 | **Max Tokens:** 2000

```
Generate a weekly email digest:
Period: {start_date} to {end_date}
Total Emails: {total}
Urgent: {urgent_count}
Action Required: {action_count}
Meetings: {meeting_count}
Spam Blocked: {spam_count}

Write a concise markdown summary with:
1. Executive summary (3-4 bullets)
2. Action items requiring attention
3. Upcoming deadlines (next 7 days)
4. Notable conversations to follow up on
```
