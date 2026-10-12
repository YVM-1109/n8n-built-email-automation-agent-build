#!/usr/bin/env python3
"""Decode an n8n execution payload (Flatted-encoded) and report node results.

Usage: python tools/inspect_execution.py [execution-json-file]
"""
import io
import json
import sys


def load(s):
    """Resolve n8n's Flatted serialization (string indices into a top-level array)."""
    arr = json.loads(s)
    memo = {}

    def resolve_idx(i):
        if i in memo:
            return memo[i]
        node = arr[i]
        if isinstance(node, dict):
            out = {}
            memo[i] = out
            for k, v in node.items():
                out[k] = walk(v)
            return out
        if isinstance(node, list):
            out = []
            memo[i] = out
            for v in node:
                out.append(walk(v))
            return out
        return node

    def walk(v):
        if isinstance(v, str) and v.isdigit() and 0 <= int(v) < len(arr):
            return resolve_idx(int(v))
        if isinstance(v, dict):
            return {k: walk(x) for k, x in v.items()}
        if isinstance(v, list):
            return [walk(x) for x in v]
        return v

    return resolve_idx(0)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else '.n8n-tmp/ex.json'
    with io.open(path, encoding='utf-8') as f:
        ex = json.load(f)['data']
    print('status:', ex.get('status'), '| finished:', ex.get('finished'),
          '| started:', ex.get('startedAt'), '| stopped:', ex.get('stoppedAt'))
    payload = load(ex['data'])
    run = payload.get('resultData', {}).get('runData', {})
    print('lastNodeExecuted:', payload.get('resultData', {}).get('lastNodeExecuted'))
    print('nodes ran:', len(run))
    for name, runs in run.items():
        for r in runs:
            items = 0
            try:
                items = len(r['data']['main'][0])
            except Exception:
                pass
            st = r.get('executionStatus')
            err = r.get('error')
            msg = ''
            if err:
                d = err.get('description') or err.get('message') or ''
                msg = ' | ERROR: %s' % str(d)[:120]
            print('  %-26s %-8s items=%d%s' % (name, st, items, msg))
    res_err = payload.get('resultData', {}).get('error')
    if res_err:
        print('workflow error:', json.dumps(res_err)[:400])
    return run


if __name__ == '__main__':
    main()
