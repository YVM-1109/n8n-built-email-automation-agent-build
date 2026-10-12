#!/usr/bin/env python3
"""Invoke a tool on an n8n instance's MCP server (streamable HTTP).

usage: python tools/mcp_call.py <tool-name> '<json-arguments>'
example: python tools/mcp_call.py search_workflows '{}'

Reads the bearer token from .n8n-cloud-api-key.txt (never printed).
"""
import io
import json
import os
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_FILE = os.path.join(ROOT, '.n8n-cloud-api-key.txt')
BASE = os.environ.get('N8N_MCP_URL',
                      'https://email-automation-ym.app.n8n.cloud/mcp-server/http')


def token():
    with io.open(TOKEN_FILE, encoding='utf-8') as f:
        t = f.read().strip()
    if not t:
        sys.exit('no token in %s' % TOKEN_FILE)
    return t


def post(payload, session=None):
    body = json.dumps(payload).encode()
    headers = {
        'Authorization': 'Bearer ' + token(),
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/event-stream',
    }
    if session:
        headers['Mcp-Session-Id'] = session
    req = urllib.request.Request(BASE, data=body, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            text = r.read().decode('utf-8', 'replace')
            return r.status, text, r.headers.get('Mcp-Session-Id')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', 'replace'), None


def parse_sse(text):
    """MCP streamable HTTP replies with 'data: {json}' SSE frames."""
    out = []
    for line in text.splitlines():
        if line.startswith('data: '):
            try:
                out.append(json.loads(line[6:]))
            except ValueError:
                pass
    if not out:
        try:
            out.append(json.loads(text))
        except ValueError:
            pass
    return out


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    tool = sys.argv[1]
    args = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}

    _status, init_text, session = post({
        'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
        'params': {'protocolVersion': '2024-11-05', 'capabilities': {},
                   'clientInfo': {'name': 'codebuff', 'version': '1.0'}},
    })
    if not parse_sse(init_text):
        sys.exit('initialize failed: %s' % init_text[:300])

    status, text, _ = post({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call',
                            'params': {'name': tool, 'arguments': args}}, session)
    frames = parse_sse(text)
    if not frames:
        sys.exit('call failed (http %s): %s' % (status, text[:300]))
    msg = frames[-1]
    if 'error' in msg:
        print(json.dumps(msg['error'], ensure_ascii=False)[:2000])
        sys.exit(1)
    result = msg.get('result', {})
    for block in result.get('content', []):
        if block.get('type') == 'text':
            print(block['text'])
    if result.get('isError'):
        sys.exit(1)


if __name__ == '__main__':
    main()
