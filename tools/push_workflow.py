#!/usr/bin/env python3
"""Push n8n-workflows/email_agent_workflow.json to the running local n8n and verify."""
import io
import json
import os
import re
import sys
import urllib.error
import urllib.request
import http.cookiejar

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BASE = os.environ.get('N8N_BASE', 'http://localhost:5678')
SRC = os.path.join(ROOT, 'n8n-workflows', 'email_agent_workflow.json')


def env(path, key, default=None):
    if not os.path.exists(path):
        return default
    with io.open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            if line.startswith(key + '='):
                return line.split('=', 1)[1].strip().strip('"').strip("'")
    return default


envpath = os.path.join(ROOT, '.env')
email = env(envpath, 'N8N_EMAIL', 'admin@localhost.local')
password = env(envpath, 'N8N_PASSWORD')
if not password:
    sys.exit('no N8N_PASSWORD in .env')

jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def call(method, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={'Content-Type': 'application/json',
                                          'Accept': 'application/json'})
    try:
        with opener.open(req, timeout=60) as r:
            body = r.read().decode('utf-8', 'replace')
            return r.status, (json.loads(body) if body else None)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', 'replace')


code, body = call('POST', '/rest/login',
                  {'emailOrLdapLoginId': email, 'password': password})
print('login:', code)
if code != 200:
    sys.exit('login failed: %s' % str(body)[:300])

code, body = call('GET', '/rest/workflows')
wfid = None
for wf in (body or {}).get('data', []):
    wfid = wf['id']
    print('found workflow:', wf['id'], wf.get('name'))
if not wfid:
    sys.exit('no workflow on server')

with io.open(SRC, encoding='utf-8') as f:
    local = json.load(f)

payload = {
    'name': local.get('name', 'Email Management Agent - Production'),
    'nodes': local['nodes'],
    'connections': local['connections'],
    'settings': local.get('settings', {}),
}
code, body = call('PATCH', '/rest/workflows/' + wfid, payload)
print('patch:', code)
if code != 200:
    sys.exit('patch failed: %s' % str(body)[:500])

code, stored = call('GET', '/rest/workflows/' + wfid)
by = {n['name']: n for n in stored['data']['nodes']}
print('stored nodes:', len(stored['data']['nodes']))
for k in ('Chain_Classification', 'Chain_Draft', 'Slack_Urgent_Alert'):
    t = by[k]['parameters']['text']
    print(' ', k, 'evaluated-expr=', t.startswith('='))
rr = by['Intent_Router']['parameters']['rules']['rules']
print('  router rules:', len(rr), 'fallback:',
      by['Intent_Router']['parameters'].get('fallbackOutput'))
print('  LM model:', by['LM_Classification']['parameters']['model'])
print('  LM cred:', list(by['LM_Classification'].get('credentials', {}).values()))
print('  mock emails:', by['Test_Email_Generator']['parameters']['jsCode'].count("mk('"))
