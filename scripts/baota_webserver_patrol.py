#!/usr/bin/env python3
import json
import os
import pathlib
import socket
import subprocess
import sys
import time
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

BASE = pathlib.Path(__file__).resolve().parent.parent
DATA_DIR = BASE / 'data'
DATA_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = DATA_DIR / 'baota_webserver_patrol_state.json'
LOG_FILE = DATA_DIR / 'baota_webserver_patrol.log'
CTRL = '/www/server/panel/script/webserver-ctl.sh'
CONF = '/www/server/panel/webserver/conf/webserver.conf'
LOCAL_PROXY_HOST = '127.0.0.1'
LOCAL_PROXY_PORT = 7891
LOCAL_UPSTREAM_HOST = '127.0.0.1'
LOCAL_UPSTREAM_PORT = 7892
LOCAL_PROXY_URL = f'http://{LOCAL_PROXY_HOST}:{LOCAL_PROXY_PORT}/'
LOCAL_UPSTREAM_URL = f'http://{LOCAL_UPSTREAM_HOST}:{LOCAL_UPSTREAM_PORT}/'
TIMEOUT = 5
MAX_AUTO_REPAIR = 2


def now_ts():
    return int(time.time())


def now_iso():
    return time.strftime('%Y-%m-%d %H:%M:%S %Z', time.localtime())


def append_log(record):
    with LOG_FILE.open('a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')


def load_state():
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding='utf-8'))
    except Exception:
        return {}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')


def check_port(host, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(TIMEOUT)
    try:
        s.connect((host, port))
        return True, 'open'
    except Exception as e:
        return False, str(e)
    finally:
        try:
            s.close()
        except Exception:
            pass


def http_probe(url):
    req = Request(url, headers={'User-Agent': 'edict-baota-patrol/1.0'})
    try:
        with urlopen(req, timeout=TIMEOUT) as resp:
            return True, resp.status, dict(resp.headers)
    except HTTPError as e:
        return True, e.code, dict(e.headers)
    except URLError as e:
        return False, str(e.reason), {}
    except Exception as e:
        return False, str(e), {}


def run_ctl(action):
    try:
        p = subprocess.run(['bash', CTRL, action], capture_output=True, text=True, timeout=20)
        return {
            'ok': p.returncode == 0,
            'returncode': p.returncode,
            'stdout': p.stdout.strip(),
            'stderr': p.stderr.strip(),
        }
    except Exception as e:
        return {'ok': False, 'returncode': -1, 'stdout': '', 'stderr': str(e)}


def main():
    state = load_state()
    record = {
        'time': now_iso(),
        'ts': now_ts(),
        'proxy_port': LOCAL_PROXY_PORT,
        'upstream_port': LOCAL_UPSTREAM_PORT,
        'actions': [],
    }

    conf_exists = os.path.exists(CONF)
    record['conf_exists'] = conf_exists

    upstream_port_ok, upstream_port_detail = check_port(LOCAL_UPSTREAM_HOST, LOCAL_UPSTREAM_PORT)
    record['upstream_port_ok'] = upstream_port_ok
    record['upstream_port_detail'] = upstream_port_detail

    proxy_port_ok, proxy_port_detail = check_port(LOCAL_PROXY_HOST, LOCAL_PROXY_PORT)
    record['proxy_port_ok'] = proxy_port_ok
    record['proxy_port_detail'] = proxy_port_detail

    proxy_http_ok, proxy_http_status, _ = http_probe(LOCAL_PROXY_URL)
    record['proxy_http_ok'] = proxy_http_ok
    record['proxy_http_status'] = proxy_http_status

    if not conf_exists:
        record['severity'] = 'critical'
        record['reason'] = 'webserver_conf_missing'
        append_log(record)
        save_state(record)
        print(json.dumps(record, ensure_ascii=False))
        return 2

    if not upstream_port_ok:
        record['severity'] = 'critical'
        record['reason'] = 'edict_upstream_down'
        append_log(record)
        save_state(record)
        print(json.dumps(record, ensure_ascii=False))
        return 2

    healthy = proxy_port_ok and proxy_http_ok
    if healthy:
        if state.get('status') == 'open':
            record['resolved'] = True
        record['status'] = 'resolved'
        record['severity'] = 'ok'
        record['reason'] = 'healthy'
        append_log(record)
        save_state(record)
        print(json.dumps(record, ensure_ascii=False))
        return 0

    repairs = int(state.get('repair_attempts', 0))
    status_res = run_ctl('status')
    record['actions'].append({'action': 'status', **status_res})

    if repairs < MAX_AUTO_REPAIR:
        start_res = run_ctl('start')
        record['actions'].append({'action': 'start', **start_res})
        time.sleep(2)
        reload_res = run_ctl('reload')
        record['actions'].append({'action': 'reload', **reload_res})
        time.sleep(1)

        proxy_port_ok2, proxy_port_detail2 = check_port(LOCAL_PROXY_HOST, LOCAL_PROXY_PORT)
        proxy_http_ok2, proxy_http_status2, _ = http_probe(LOCAL_PROXY_URL)
        record['post_repair_proxy_port_ok'] = proxy_port_ok2
        record['post_repair_proxy_port_detail'] = proxy_port_detail2
        record['post_repair_proxy_http_ok'] = proxy_http_ok2
        record['post_repair_proxy_http_status'] = proxy_http_status2

        if proxy_port_ok2 and proxy_http_ok2:
            record['status'] = 'resolved'
            record['severity'] = 'warning'
            record['reason'] = 'auto_repaired'
            record['repair_attempts'] = repairs + 1
            append_log(record)
            save_state({'status': 'resolved', 'repair_attempts': 0, 'last_ok': record['ts'], 'last_record': record})
            print(json.dumps(record, ensure_ascii=False))
            return 0

        record['status'] = 'open'
        record['severity'] = 'critical'
        record['reason'] = 'auto_repair_failed'
        record['repair_attempts'] = repairs + 1
        append_log(record)
        save_state({'status': 'open', 'repair_attempts': repairs + 1, 'last_record': record})
        print(json.dumps(record, ensure_ascii=False))
        return 1

    record['status'] = 'open'
    record['severity'] = 'critical'
    record['reason'] = 'max_auto_repair_exceeded'
    record['repair_attempts'] = repairs
    append_log(record)
    save_state({'status': 'open', 'repair_attempts': repairs, 'last_record': record})
    print(json.dumps(record, ensure_ascii=False))
    return 1


if __name__ == '__main__':
    sys.exit(main())
