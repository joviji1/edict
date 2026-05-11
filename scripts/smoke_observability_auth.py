#!/usr/bin/env python3
"""Authenticated live smoke for edict dashboard observability panel.

Read-only. Password is accepted only via --password or EDICT_DASHBOARD_PASSWORD;
outputs never include the raw JWT token or password.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request


def _read_json_response(req: urllib.request.Request, timeout: int) -> tuple[int, dict]:
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode('utf-8'))
        return getattr(resp, 'status', 200), payload


def run_smoke(
    password: str,
    *,
    base_url: str = 'http://127.0.0.1:7892',
    query: str = 'token',
    limit: int = 3,
    timeout: int = 10,
) -> dict:
    base_url = base_url.rstrip('/')
    login_payload = json.dumps({'password': password}, ensure_ascii=False).encode('utf-8')
    login_req = urllib.request.Request(
        f'{base_url}/api/auth/login',
        data=login_payload,
        method='POST',
        headers={
            'Content-Type': 'application/json; charset=utf-8',
            'Accept': 'application/json',
            'User-Agent': 'edict-observability-auth-smoke/1.0',
        },
    )
    login_status, login_body = _read_json_response(login_req, timeout)
    token = login_body.get('token') if isinstance(login_body, dict) else None
    if login_status != 200 or not login_body.get('ok') or not token:
        return {
            'ok': False,
            'stage': 'login',
            'httpStatus': login_status,
            'error': login_body.get('error') or 'login failed',
        }

    params = urllib.parse.urlencode({'limit': str(limit), 'q': query})
    panel_req = urllib.request.Request(
        f'{base_url}/api/observability-panel?{params}',
        method='GET',
        headers={
            'Accept': 'application/json',
            'Authorization': f'Bearer {token}',
            'User-Agent': 'edict-observability-auth-smoke/1.0',
        },
    )
    panel_status, panel = _read_json_response(panel_req, timeout)
    gateway_auth = (((panel or {}).get('tokens') or {}).get('gatewayAuth') or {}) if isinstance(panel, dict) else {}
    return {
        'ok': bool(isinstance(panel, dict) and panel.get('ok') and panel_status == 200),
        'stage': 'observability-panel',
        'httpStatus': panel_status,
        'query': panel.get('query') if isinstance(panel, dict) else query,
        'stats': panel.get('stats') if isinstance(panel, dict) else None,
        'sources': panel.get('sources') if isinstance(panel, dict) else None,
        'gatewayAuth': {
            'configured': bool(gateway_auth.get('configured')),
            'redactedToken': gateway_auth.get('redactedToken'),
            'path': gateway_auth.get('path'),
        },
        'tokenRedacted': bool(gateway_auth.get('redactedToken')),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Authenticated observability-panel live smoke (read-only).')
    parser.add_argument('--base-url', default='http://127.0.0.1:7892')
    parser.add_argument('--query', default='token')
    parser.add_argument('--limit', type=int, default=3)
    parser.add_argument('--timeout', type=int, default=10)
    parser.add_argument('--password', default=os.environ.get('EDICT_DASHBOARD_PASSWORD', ''))
    args = parser.parse_args(argv)
    if not args.password:
        print(json.dumps({
            'ok': False,
            'error': 'missing password: pass --password or set EDICT_DASHBOARD_PASSWORD',
        }, ensure_ascii=False), file=sys.stderr)
        return 2
    try:
        result = run_smoke(
            args.password,
            base_url=args.base_url,
            query=args.query,
            limit=args.limit,
            timeout=args.timeout,
        )
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0 if result.get('ok') else 1
    except Exception as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
