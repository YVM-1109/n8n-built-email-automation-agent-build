#!/usr/bin/env python3
"""Rebuild email_agent_workflow.json for n8n 2.42 compatibility.

Preserves the original tested Code nodes verbatim where possible and fixes the
structural problems of the shipped workflow:

  * AI model nodes (lmChatOpenAi) are wired via ai_languageModel into
    Basic LLM Chain nodes instead of invalid main connections
  * Merge nodes restore email context after each LLM call (chain output is {text} only)
  * IMAP trigger/move replaced with Gmail API nodes (trigger, labels, drafts)
  * Slack uses channelId/select/text (v2 params) instead of the removed `channel`
  * Notion uses resource=databasePage/create instead of non-existent documentId
  * Switch rules use v2 {operation, value2, output} shape + fallbackOutput
  * Dangling errorWorkflow reference removed
  * Every integration branch is fail-safe (onError=continue) and analytics is
    logged before the action so context is never lost
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, 'n8n-workflows', 'email_agent_workflow.json')

with open(SRC, encoding='utf-8') as f:
    original = json.load(f)

orig_code = {n['name']: n['parameters']['jsCode']
             for n in original['nodes'] if n['type'] == 'n8n-nodes-base.code'}

OPENAI_CRED = {'openAiApi': {'id': 'MByJvgvEPqbTZQUE', 'name': 'OpenRouter API'}}

CLASSIFY_PROMPT = """=You are an expert email triage agent. Analyze this email and return ONLY JSON (no markdown, no explanation):
{
  "intent": "urgent|action_required|informational|newsletter|spam|meeting_request",
  "confidence": 0.0-1.0,
  "urgency_score": 1-10,
  "sentiment": "positive|neutral|negative",
  "entities": {
    "deadlines": [],
    "action_items": [],
    "people_mentioned": [],
    "projects": []
  },
  "suggested_action": "reply|forward|archive|flag|create_task|schedule_meeting|quarantine",
  "summary": "2-3 sentence summary"
}

Email:
Subject: {{ $json.subject }}
From: {{ $json.senderName }} <{{ $json.senderEmail }}>
Date: {{ $json.date }}
Content: {{ $json.textContent }}"""

DRAFT_PROMPT = """=Draft a professional email response.

Original Email:
From: {{ $json.senderName }} <{{ $json.senderEmail }}>
Subject: {{ $json.subject }}
Content: {{ $json.textContent }}

Context:
- Intent: {{ $json.classification.intent }}
- Action Items: {{ (($json.classification.entities || {}).action_items || []).join(', ') }}
- Tone: Professional but warm

Return ONLY the email body text."""

SLACK_TEXT = "=🚨 *URGENT EMAIL*\n\nFrom: {{ $json.senderName }}\nSubject: {{ $json.subject }}\nUrgency: {{ $json.classification.urgency_score }}/10\nSummary: {{ $json.classification.summary }}"

DEDUP_CODE = """// Deduplication Engine (multi-item safe)
const seen = $getWorkflowStaticData('global').seen || {};
const now = Date.now();
const out = [];
let auto = 0;
for (const item of $input.all()) {
  const j = item.json;
  const messageId = String(j.messageId || j.id || ((j.subject || '') + '|' + (j.date || '')) || JSON.stringify(j).substring(0, 120));
  let hash = messageId.replace(/[^a-zA-Z0-9]/g, '').substring(0, 64);
  if (!hash) hash = 'auto' + now + '_' + (auto++);
  if (seen[hash]) {
    out.push({ json: { ...j, skipped: true, reason: 'duplicate', messageId } });
    continue;
  }
  seen[hash] = now;
  out.push({ json: { ...j, dedupHash: hash, skipped: false } });
}
// keep the static map bounded
const keys = Object.keys(seen);
if (keys.length > 5000) {
  keys.sort((a, b) => seen[a] - seen[b]);
  for (const k of keys.slice(0, keys.length - 5000)) delete seen[k];
}
$getWorkflowStaticData('global').seen = seen;
return out;"""

EXTRACT_CODE = """// Content Extraction & Normalization (Gmail simple + IMAP/legacy shapes)
const parseAddr = (s) => {
  const m = String(s || '').match(/^\\s*"?([^"<]*)"?\\s*<([^>]+)>\\s*$/);
  if (m) return { name: (m[1] || '').trim(), address: m[2].trim() };
  const t = String(s || '').trim();
  return { name: t, address: t || 'unknown' };
};
const header = (headers, name) => {
  if (!Array.isArray(headers)) return '';
  const h = headers.find(x => (x.name || x.key || '').toLowerCase() === name.toLowerCase());
  return h ? (h.value || '') : '';
};
const stripHtml = (s) => String(s).replace(/<[^>]*>/g, ' ').replace(/\\s+/g, ' ').trim();
const normList = (v) => {
  if (!v) return [];
  if (Array.isArray(v)) return v.map(x => (typeof x === 'string' ? x : (x && x.address) || String(x)));
  if (v.value) return v.value.map(x => x.address || String(x));
  if (typeof v === 'string') return v.split(',').map(s => s.trim()).filter(Boolean);
  return [];
};
const results = [];
for (const item of $input.all()) {
  const e = item.json;
  let senderEmail = 'unknown';
  let senderName = 'unknown';
  const from = e.from;
  if (typeof from === 'string' && from) {
    const p = parseAddr(from);
    senderEmail = p.address;
    senderName = p.name || p.address;
  } else if (from && from.value && from.value[0]) {
    senderEmail = from.value[0].address || 'unknown';
    senderName = from.value[0].name || senderEmail;
  } else if (from && from.address) {
    senderEmail = from.address;
    senderName = from.name || from.address;
  } else {
    const h = header(e.headers, 'From');
    if (h) {
      const p = parseAddr(h);
      senderEmail = p.address;
      senderName = p.name || p.address;
    }
  }
  const subject = e.subject || header(e.headers, 'Subject') || '(No Subject)';
  const date = e.date || header(e.headers, 'Date') || null;
  let textContent = e.textPlain || e.text || e.body || e.snippet || '';
  if (typeof textContent !== 'string') textContent = '';
  if (!textContent && e.textHtml) textContent = stripHtml(e.textHtml);
  if (!textContent && e.html) textContent = stripHtml(e.html);
  results.push({ json: {
    messageId: e.messageId || e.id || (subject + '_' + date),
    threadId: e.threadId || null,
    subject,
    senderEmail,
    senderName,
    to: normList(e.to || header(e.headers, 'To')),
    cc: normList(e.cc || header(e.headers, 'Cc')),
    date,
    textContent: textContent.substring(0, 8000),
    htmlContent: e.textHtml || e.html || '',
    attachments: (e.attachments || []).map(a => ({ filename: a.filename || a.name, size: a.size })),
    dedupHash: e.dedupHash,
    processedAt: new Date().toISOString(),
  }});
}
return results;"""

ANALYTICS_CODE = """// Log execution for analytics (one entry per item, context-safe)
const results = [];
for (const item of $input.all()) {
  const data = item.json;
  const logEntry = {
    executionId: $execution.id,
    timestamp: new Date().toISOString(),
    messageId: data.messageId || data.id || null,
    sender: data.senderEmail || null,
    subject: (data.subject || '').substring(0, 100),
    intent: data.classification?.intent || 'unknown',
    confidence: data.classification?.confidence || 0,
    urgencyScore: data.classification?.urgency_score || 0,
    actionTaken: data.routingDecision || 'none',
    skipped: data.skipped === true,
    success: true,
  };
  console.log('ANALYTICS_LOG:', JSON.stringify(logEntry));
  results.push({ json: logEntry });
}
return results;"""

TEST_EMAIL_CODE = """// Generates mock emails shaped like real inbox messages, for manual testing
// without touching Gmail. Timestamped IDs so deduplication lets each run through.
const now = Date.now();
const iso = new Date(now).toISOString();
const mk = (id, subject, fromAddr, fromName, body) => ({
  json: {
    messageId: '<mock-' + id + '-' + now + '@demo.local>',
    subject,
    date: iso,
    from: { value: [{ address: fromAddr, name: fromName }] },
    to: { value: [{ address: 'you@example.com', name: 'You' }] },
    cc: { value: [] },
    textPlain: body,
    attachments: [],
  },
});
return [
  mk('urgent', 'URGENT: Production outage - action required today', 'ops-lead@example.com', 'Dana Ops',
    'Our production server has been down since 14:00 and customers are affected. ' +
    'Please investigate immediately and reply with a status update by 5 pm today. ' +
    'Also 10/09/2026 works for the postmortem meeting at 3:30 pm.'),
  mk('newsletter', 'Your weekly newsletter digest', 'news@techweekly.example', 'Tech Weekly',
    'Top stories this week: five tools worth watching. If you no longer wish to receive ' +
    'these emails, click unsubscribe.'),
  mk('action-review', 'Action required: review Q4 vendor contract before Friday', 'contracts@acme-vendors.example', 'Ava Vendor',
    'Please review the updated vendor contract and send me your redlines by Friday. ' +
    'Legal needs our sign-off before the renewal window closes on 10/16/2026.'),
];"""


def node(name, ntype, tv, params, pos, cred=None, nid=None, on_error=None):
    n = {
        'parameters': params,
        'id': nid or name.lower().replace('_', '-'),
        'name': name,
        'type': ntype,
        'typeVersion': tv,
        'position': pos,
    }
    if cred:
        n['credentials'] = cred
    if on_error:
        n['onError'] = on_error
    return n


FAILSAFE = 'continueRegularOutput'

nodes = [
    # ---- triggers -------------------------------------------------------
    node('Manual Trigger', 'n8n-nodes-base.manualTrigger', 1, {}, [0, 320], nid='trigger-manual'),
    node('Gmail_Trigger', 'n8n-nodes-base.gmailTrigger', 1.4, {
        'authentication': 'oAuth2',
        'event': 'messageReceived',
        # Must stay False: the Gmail trigger's "Simplify" output drops the
        # From/To/Date headers, so Content_Extraction reports senderName and
        # senderEmail as "unknown" and drafts/alerts lose the real sender.
        'simple': False,
        'maxResults': 10,
        'filters': {'labelIds': ['INBOX']},
    }, [0, 0], nid='trigger-gmail'),
    node('Test_Email_Generator', 'n8n-nodes-base.code', 2, {'jsCode': TEST_EMAIL_CODE}, [240, 320], nid='test-gen'),

    # ---- pipeline -------------------------------------------------------
    node('Deduplication_Check', 'n8n-nodes-base.code', 2, {'jsCode': DEDUP_CODE}, [460, 160], nid='dedup'),
    node('Filter_Duplicates', 'n8n-nodes-base.if', 2, {
        'conditions': {
            'options': {'caseSensitive': True, 'leftValue': '', 'typeValidation': 'strict'},
            'conditions': [{'id': 'cond-1', 'leftValue': '={{ $json.skipped }}', 'rightValue': False,
                            'operator': {'type': 'boolean', 'operation': 'equals'}}],
            'combinator': 'and',
        },
    }, [680, 160], nid='filter-dup'),
    node('Content_Extraction', 'n8n-nodes-base.code', 2, {'jsCode': EXTRACT_CODE}, [900, 100], nid='extract'),

    # ---- AI classification (model -> chain -> merge -> parse) -----------
    node('LM_Classification', '@n8n/n8n-nodes-langchain.lmChatOpenAi', 1.3, {
        'model': {'__rl': True, 'mode': 'list', 'value': 'poolside/laguna-s-2.1'},
        'options': {'baseURL': 'https://openrouter.ai/api/v1'},
    }, [1120, -180], cred=OPENAI_CRED, nid='lm-classify'),
    node('Chain_Classification', '@n8n/n8n-nodes-langchain.chainLlm', 1.9, {
        'promptType': 'define',
        'text': CLASSIFY_PROMPT,
        'hasOutputParser': False,
    }, [1120, 40], cred=OPENAI_CRED, nid='chain-classify'),
    node('Merge_Classify', 'n8n-nodes-base.merge', 2, {
        'mode': 'combine',
        'combinationMode': 'mergeByPosition',
        'options': {'clashHandling': {'values': {'resolveClash': 'preferInput2', 'mergeMode': 'deepMerge', 'overrideEmpty': False}}},
    }, [1340, 100], nid='merge-classify'),
    node('Parse_Classification', 'n8n-nodes-base.code', 2, {'jsCode': orig_code['Parse_Classification']}, [1560, 100], nid='parse'),
    node('Intent_Router', 'n8n-nodes-base.switch', 2, {
        'mode': 'rules',
        'dataType': 'string',
        'value1': '={{ $json.classification.intent }}',
        'rules': {'rules': [
            {'operation': 'equal', 'value2': 'urgent', 'output': 0, 'outputKey': 'urgent'},
            {'operation': 'equal', 'value2': 'action_required', 'output': 1, 'outputKey': 'action_required'},
            {'operation': 'equal', 'value2': 'meeting_request', 'output': 2, 'outputKey': 'meeting_request'},
            {'operation': 'equal', 'value2': 'newsletter', 'output': 3, 'outputKey': 'newsletter'},
            {'operation': 'equal', 'value2': 'spam', 'output': 4, 'outputKey': 'spam'},
            # catch-all so unmatched intents (e.g. informational) land on output 5
            {'operation': 'notEqual', 'value2': '__default__', 'output': 5, 'outputKey': 'default'},
        ]},
        'fallbackOutput': 5,
    }, [1780, 100], nid='router'),

    # ---- branch: urgent -> Slack ---------------------------------------
    node('Slack_Urgent_Alert', 'n8n-nodes-base.slack', 2.1, {
        'authentication': 'accessToken',
        'resource': 'message',
        'operation': 'post',
        'select': 'channel',
        'channelId': {'__rl': True, 'mode': 'name', 'value': '={{ $env.SLACK_ALERT_CHANNEL || "#email-alerts" }}'},
        'messageType': 'text',
        'text': SLACK_TEXT,
        'otherOptions': {'includeLinkToWorkflow': False},
    }, [2020, -300], nid='slack-alert', on_error=FAILSAFE),

    # ---- branch: action_required -> draft (chain+merge) -> Gmail + Notion
    node('LM_Draft', '@n8n/n8n-nodes-langchain.lmChatOpenAi', 1.3, {
        'model': {'__rl': True, 'mode': 'list', 'value': 'poolside/laguna-s-2.1'},
        'options': {'baseURL': 'https://openrouter.ai/api/v1'},
    }, [2020, -360], cred=OPENAI_CRED, nid='lm-draft'),
    node('Chain_Draft', '@n8n/n8n-nodes-langchain.chainLlm', 1.9, {
        'promptType': 'define',
        'text': DRAFT_PROMPT,
        'hasOutputParser': False,
    }, [2020, -140], cred=OPENAI_CRED, nid='chain-draft'),
    node('Merge_Draft', 'n8n-nodes-base.merge', 2, {
        'mode': 'combine',
        'combinationMode': 'mergeByPosition',
        'options': {'clashHandling': {'values': {'resolveClash': 'preferInput2', 'mergeMode': 'deepMerge', 'overrideEmpty': False}}},
    }, [2240, -140], nid='merge-draft'),
    node('Gmail_Save_Draft', 'n8n-nodes-base.gmail', 2.2, {
        'resource': 'draft',
        'operation': 'create',
        'subject': '={{ "Re: " + $json.subject }}',
        'emailType': 'text',
        'message': '={{ $json.text }}',
        'options': {'sendTo': '={{ $json.senderEmail }}'},
    }, [2470, -220], nid='gmail-draft', on_error=FAILSAFE),
    node('Notion_Create_Task', 'n8n-nodes-base.notion', 2.2, {
        'authentication': 'apiKey',
        'resource': 'databasePage',
        'operation': 'create',
        'databaseId': {'__rl': True, 'mode': 'id', 'value': '={{ $env.NOTION_TASKS_DB }}'},
        'title': '={{ $json.subject }}',
        'simple': True,
        'propertiesUi': {'propertyValues': [
            {'propertyName': 'Status', 'value': 'To Do'},
            {'propertyName': 'Priority', 'value': 'High'},
            {'propertyName': 'Source', 'value': '={{ $json.senderEmail }}'},
            {'propertyName': 'Summary', 'value': '={{ $json.classification.summary }}'},
        ]},
    }, [2470, -60], nid='notion-task', on_error=FAILSAFE),

    # ---- branch: meeting_request ---------------------------------------
    node('Extract_Meeting_Dates', 'n8n-nodes-base.code', 2,
         {'jsCode': orig_code['Extract_Meeting_Dates']}, [2020, 80], nid='meeting'),

    # ---- branch: newsletter -> label + archive --------------------------
    node('Gmail_Label_Newsletter', 'n8n-nodes-base.gmail', 2.2, {
        'resource': 'message',
        'operation': 'addLabels',
        'messageId': '={{ $json.messageId }}',
        'labelIds': ['Label_000'],
    }, [2020, 260], nid='gmail-news-label', on_error=FAILSAFE),
    node('Gmail_Archive_Newsletter', 'n8n-nodes-base.gmail', 2.2, {
        'resource': 'message',
        'operation': 'removeLabels',
        'messageId': '={{ $json.id }}',
        'labelIds': ['INBOX'],
    }, [2260, 260], nid='gmail-news-archive', on_error=FAILSAFE),

    # ---- branch: spam -> quarantine ------------------------------------
    node('Gmail_Quarantine_Spam', 'n8n-nodes-base.gmail', 2.2, {
        'resource': 'message',
        'operation': 'addLabels',
        'messageId': '={{ $json.messageId }}',
        'labelIds': ['SPAM'],
    }, [2020, 440], nid='gmail-spam-label', on_error=FAILSAFE),
    node('Gmail_Unlist_Spam', 'n8n-nodes-base.gmail', 2.2, {
        'resource': 'message',
        'operation': 'removeLabels',
        'messageId': '={{ $json.id }}',
        'labelIds': ['INBOX'],
    }, [2260, 440], nid='gmail-spam-unlist', on_error=FAILSAFE),

    # ---- analytics fan-in ----------------------------------------------
    node('Analytics_Logger', 'n8n-nodes-base.code', 2, {'jsCode': ANALYTICS_CODE}, [2720, 100], nid='analytics'),
]


def main_out(src, idx, targets):
    return {'node': src, 'type': 'main', 'index': idx} if False else None


connections = {
    'Manual Trigger': {'main': [[{'node': 'Test_Email_Generator', 'type': 'main', 'index': 0}]]},
    'Gmail_Trigger': {'main': [[{'node': 'Deduplication_Check', 'type': 'main', 'index': 0}]]},
    'Test_Email_Generator': {'main': [[{'node': 'Deduplication_Check', 'type': 'main', 'index': 0}]]},
    'Deduplication_Check': {'main': [[{'node': 'Filter_Duplicates', 'type': 'main', 'index': 0}]]},
    'Filter_Duplicates': {'main': [
        [{'node': 'Content_Extraction', 'type': 'main', 'index': 0}],
        [{'node': 'Analytics_Logger', 'type': 'main', 'index': 0}],
    ]},
    # content feeds both the merge (context) and the chain (prompt)
    'Content_Extraction': {'main': [[
        {'node': 'Merge_Classify', 'type': 'main', 'index': 0},
        {'node': 'Chain_Classification', 'type': 'main', 'index': 0},
    ]]},
    'LM_Classification': {'ai_languageModel': [[{'node': 'Chain_Classification', 'type': 'ai_languageModel', 'index': 0}]]},
    'Chain_Classification': {'main': [[{'node': 'Merge_Classify', 'type': 'main', 'index': 1}]]},
    'Merge_Classify': {'main': [[{'node': 'Parse_Classification', 'type': 'main', 'index': 0}]]},
    'Parse_Classification': {'main': [[{'node': 'Intent_Router', 'type': 'main', 'index': 0}]]},
    'Intent_Router': {'main': [
        # 0 urgent
        [{'node': 'Slack_Urgent_Alert', 'type': 'main', 'index': 0},
         {'node': 'Analytics_Logger', 'type': 'main', 'index': 0}],
        # 1 action_required
        [{'node': 'Chain_Draft', 'type': 'main', 'index': 0},
         {'node': 'Merge_Draft', 'type': 'main', 'index': 0},
         {'node': 'Analytics_Logger', 'type': 'main', 'index': 0}],
        # 2 meeting_request
        [{'node': 'Extract_Meeting_Dates', 'type': 'main', 'index': 0},
         {'node': 'Analytics_Logger', 'type': 'main', 'index': 0}],
        # 3 newsletter
        [{'node': 'Gmail_Label_Newsletter', 'type': 'main', 'index': 0},
         {'node': 'Analytics_Logger', 'type': 'main', 'index': 0}],
        # 4 spam
        [{'node': 'Gmail_Quarantine_Spam', 'type': 'main', 'index': 0},
         {'node': 'Analytics_Logger', 'type': 'main', 'index': 0}],
        # 5 default / informational
        [{'node': 'Analytics_Logger', 'type': 'main', 'index': 0}],
    ]},
    'LM_Draft': {'ai_languageModel': [[{'node': 'Chain_Draft', 'type': 'ai_languageModel', 'index': 0}]]},
    'Chain_Draft': {'main': [[{'node': 'Merge_Draft', 'type': 'main', 'index': 1}]]},
    'Merge_Draft': {'main': [[
        {'node': 'Gmail_Save_Draft', 'type': 'main', 'index': 0},
        {'node': 'Notion_Create_Task', 'type': 'main', 'index': 0},
    ]]},
    'Extract_Meeting_Dates': {'main': [[{'node': 'Analytics_Logger', 'type': 'main', 'index': 0}]]},
    'Gmail_Label_Newsletter': {'main': [[{'node': 'Gmail_Archive_Newsletter', 'type': 'main', 'index': 0}]]},
    'Gmail_Archive_Newsletter': {'main': [[{'node': 'Analytics_Logger', 'type': 'main', 'index': 0}]]},
    'Gmail_Quarantine_Spam': {'main': [[{'node': 'Gmail_Unlist_Spam', 'type': 'main', 'index': 0}]]},
    'Gmail_Unlist_Spam': {'main': [[{'node': 'Analytics_Logger', 'type': 'main', 'index': 0}]]},
}

workflow = {
    'name': original['name'],
    'nodes': nodes,
    'connections': connections,
    'settings': {
        'executionOrder': 'v1',
        'saveDataErrorExecution': 'all',
        'saveDataSuccessExecution': 'all',
        'saveExecutionProgress': True,
        'timezone': 'UTC',
    },
    'tags': [],
}

out_path = SRC
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(workflow, f, indent=2, ensure_ascii=False)
    f.write('\n')

# structural self-check
names = [n['name'] for n in nodes]
assert len(names) == len(set(names)), 'duplicate node names'
node_set = set(names)
for src, outs in connections.items():
    assert src in node_set, f'unknown connection source {src}'
    for ctype, groups in outs.items():
        for group in groups:
            for c in group:
                assert c['node'] in node_set, f"unknown target {c['node']}"
print(f'OK: wrote {out_path} with {len(nodes)} nodes and {len(connections)} connection sources')
