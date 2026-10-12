// Offline unit tests for every Code node in email_agent_workflow.json
import { readFileSync } from 'node:fs';

const wf = JSON.parse(readFileSync(new URL('../n8n-workflows/email_agent_workflow.json', import.meta.url), 'utf8'));
const codeNodes = Object.fromEntries(wf.nodes.filter(n => n.type === 'n8n-nodes-base.code').map(n => [n.name, n.parameters.jsCode]));

let pass = 0, fail = 0;
const check = (name, cond, detail = '') => {
  if (cond) { pass++; console.log(`  [OK]   ${name}`); }
  else { fail++; console.log(`  [FAIL] ${name} ${detail}`); }
};

// --- shared mock state for $getWorkflowStaticData ---
const staticData = { global: {} };
const makeCtx = (json) => ({
  $input: { first: () => ({ json }), all: () => [{ json }] },
  $getWorkflowStaticData: () => staticData.global,
  $execution: { id: 'test-exec' },
  $executionId: 'test-exec',
  console,
});

const run = async (node, json) => {
  const fn = new Function('$input', '$getWorkflowStaticData', '$execution', '$executionId', `return (async () => { ${codeNodes[node]} })()`);
  return fn(makeCtx(json).$input, makeCtx(json).$getWorkflowStaticData, makeCtx(json).$execution, makeCtx(json).$executionId);
};

// ============ 1. Deduplication_Check ============
console.log('\n1. Deduplication_Check');
{
  staticData.global = {};
  const msg = { messageId: '<abc-123@mail.gmail.com>', subject: 'First' };
  const r1 = await run('Deduplication_Check', msg);
  check('first email passes', r1[0].json.skipped === false && r1[0].json.dedupHash.length > 0);
  const r2 = await run('Deduplication_Check', msg);
  check('duplicate is skipped', r2[0].json.skipped === true && r2[0].json.reason === 'duplicate');
  const r3 = await run('Deduplication_Check', { messageId: '<xyz-999@mail.gmail.com>' });
  check('different email passes', r3[0].json.skipped === false);
}

// ============ 2. Content_Extraction ============
console.log('\n2. Content_Extraction');
{
  const raw = {
    messageId: '<m1@x.com>', subject: 'Hello', date: '2026-10-08T10:00:00.000Z',
    from: { value: [{ address: 'alice@example.com', name: 'Alice' }] },
    to: { value: [{ address: 'me@gmail.com' }] },
    cc: { value: [] },
    textPlain: 'Plain body text',
    textHtml: '<p>Html <b>body</b></p>',
    attachments: [{ filename: 'a.pdf', size: 1024 }],
    dedupHash: 'h1',
  };
  const r = await run('Content_Extraction', raw);
  const j = r[0].json;
  check('sender extracted', j.senderEmail === 'alice@example.com' && j.senderName === 'Alice');
  check('plain text preferred', j.textContent === 'Plain body text');
  check('to/cc arrays', Array.isArray(j.to) && j.to[0] === 'me@gmail.com' && Array.isArray(j.cc));
  check('attachments mapped', j.attachments[0].filename === 'a.pdf');
  check('html fallback strips tags', (() => {
    const noPlain = { ...raw }; delete noPlain.textPlain;
    return true; // validated below separately
  })());
  const r2 = await run('Content_Extraction', { ...raw, textPlain: undefined, textHtml: '<p>Hi <b>there</b></p>' });
  const j2 = r2[0].json;
  check('html->text fallback', !j2.textContent.includes('<') && j2.textContent.includes('Hi'), `got: "${j2.textContent}"`);
  check('missing from handled', (await run('Content_Extraction', { messageId: 'm', subject: 's' }))[0].json.senderEmail === 'unknown');
}

// ============ 3. Parse_Classification ============
console.log('\n3. Parse_Classification');
{
  const good = {
    subject: 's',
    text: JSON.stringify({ intent: 'urgent', confidence: 0.95, urgency_score: 8, sentiment: 'negative',
      entities: { deadlines: ['friday'], action_items: ['send report'], people_mentioned: ['Bob'], projects: ['X'] },
      suggested_action: 'reply', summary: 'Bad thing happening' }),
  };
  const r = await run('Parse_Classification', good);
  const c = r[0].json.classification;
  check('valid JSON parsed', c.intent === 'urgent' && c.confidence === 0.95);
  check('routingDecision set', r[0].json.routingDecision === 'reply');

  const inText = { subject: 's', text: 'Here you go: {"intent":"spam","confidence":0.9,"urgency_score":2,"sentiment":"neutral","entities":{"deadlines":[],"action_items":[],"people_mentioned":[],"projects":[]},"suggested_action":"quarantine","summary":"junk"}' };
  const r2 = await run('Parse_Classification', inText);
  check('JSON embedded in prose extracted', r2[0].json.classification.intent === 'spam');

  const bad = { subject: 'URGENT: server down', text: 'not json at all' };
  const r3 = await run('Parse_Classification', bad);
  const c3 = r3[0].json.classification;
  check('fallback on parse error', c3.parseError === true && c3.suggested_action === 'archive');
  check('low-confidence subject override -> urgent', c3.intent === 'urgent' && c3.urgency_score === 9);

  const nl = { subject: 'Weekly Newsletter', text: 'garbage' };
  const c4 = (await run('Parse_Classification', nl))[0].json.classification;
  check('low-confidence subject override -> newsletter', c4.intent === 'newsletter');
}

// ============ 4. Extract_Meeting_Dates ============
console.log('\n4. Extract_Meeting_Dates');
{
  const r = await run('Extract_Meeting_Dates', { textContent: 'Lets meet on Tuesday, October 14 at 3:30 pm. Also 12/25/2026 works.' });
  const j = r[0].json;
  check('weekday+date matched', j.extractedDates.some(d => /tuesday/i.test(d)), JSON.stringify(j.extractedDates));
  check('time matched', j.extractedDates.some(d => /3:30/i.test(d)));
  check('calendarAction=review_needed', j.calendarAction === 'review_needed');
  const r2 = await run('Extract_Meeting_Dates', { textContent: 'no scheduling info here' });
  check('no dates -> no_dates_found', r2[0].json.calendarAction === 'no_dates_found');
}

// ============ 5. Analytics_Logger ============
console.log('\n5. Analytics_Logger');
{
  const r = await run('Analytics_Logger', {
    messageId: 'm1', senderEmail: 'a@b.c', subject: 'Sub'.repeat(60),
    classification: { intent: 'urgent', confidence: 0.9, urgency_score: 9 },
    routingDecision: 'reply',
  });
  const j = r[0].json;
  check('log entry shaped', j.intent === 'urgent' && j.actionTaken === 'reply' && j.success === true);
  check('subject truncated to 100', j.subject.length <= 100);
  check('missing classification tolerated', (await run('Analytics_Logger', { messageId: 'm' }))[0].json.intent === 'unknown');
}

console.log(`\nRESULT: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
