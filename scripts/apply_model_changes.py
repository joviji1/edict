#!/usr/bin/env python3
"""应用 data/pending_model_changes.json → openclaw.json，并重启 Gateway"""
import datetime
import glob
import json
import logging
import os
import pathlib
import shutil
import subprocess

from file_lock import atomic_json_write
from utils import get_openclaw_home

_IS_WINDOWS = os.name == 'nt'
if _IS_WINDOWS:
    import msvcrt
else:
    import fcntl

log = logging.getLogger('model_change')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(message)s', datefmt='%H:%M:%S')

BASE = pathlib.Path(__file__).parent.parent
DATA = BASE / 'data'
OPENCLAW_HOME = get_openclaw_home()
OPENCLAW_CFG = OPENCLAW_HOME / 'openclaw.json'
PENDING = DATA / 'pending_model_changes.json'
CHANGE_LOG = DATA / 'model_change_log.json'
MAX_BACKUPS = 10
GATEWAY_RESTART_TIMEOUT = 60
APPLY_LOCK = DATA / '.apply_model_changes.lock'


def rj(path, default):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def cleanup_backups():
    """只保留最近 MAX_BACKUPS 个备份"""
    pattern = str(OPENCLAW_CFG.parent / 'openclaw.json.bak.model-*')
    baks = sorted(glob.glob(pattern))
    for old in baks[:-MAX_BACKUPS]:
        try:
            pathlib.Path(old).unlink()
        except OSError:
            pass


def _normalize_model_value(model_value):
    if isinstance(model_value, str):
        return model_value.strip()
    if isinstance(model_value, dict):
        return str(model_value.get('primary') or model_value.get('id') or '').strip()
    return ''


def _agent_effective_model(agent_cfg, default_model, fallback_models):
    explicit_model = _normalize_model_value(agent_cfg.get('model', ''))
    if explicit_model:
        return explicit_model
    if default_model:
        return default_model
    fallback_models = [m for m in fallback_models if m]
    if len(fallback_models) == 1 and agent_cfg.get('model') is None:
        return fallback_models[0]
    return ''


def _try_acquire_apply_lock():
    APPLY_LOCK.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(APPLY_LOCK), os.O_CREAT | os.O_RDWR)
    try:
        if _IS_WINDOWS:
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        else:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd
    except (BlockingIOError, OSError):
        os.close(fd)
        return None


def _release_apply_lock(fd):
    if fd is None:
        return
    try:
        if _IS_WINDOWS:
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        else:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def main():
    lock_fd = _try_acquire_apply_lock()
    if lock_fd is None:
        log.info('another apply_model_changes is already running; skip this round')
        return
    try:
        if not PENDING.exists():
            return
        pending = rj(PENDING, [])
        if not pending:
            return

        cfg = rj(OPENCLAW_CFG, {})
        agents_cfg = cfg.get('agents', {})
        agents_list = agents_cfg.get('list', [])
        defaults_model_cfg = agents_cfg.get('defaults', {}).get('model', {})
        default_model = _normalize_model_value(defaults_model_cfg)
        fallback_models = []
        if isinstance(defaults_model_cfg, dict):
            fallback_models = [_normalize_model_value(m) for m in defaults_model_cfg.get('fallbacks', [])]
        fallback_models = [m for m in fallback_models if m and m != default_model]
        old_cfg_text = json.dumps(cfg, ensure_ascii=False, sort_keys=True)

        applied, errors = [], []
        for change in pending:
            ag_id = change.get('agentId', '').strip()
            new_model = change.get('model', '').strip()
            if not ag_id or not new_model:
                errors.append({'change': change, 'error': 'missing fields'})
                continue
            found = False
            for ag in agents_list:
                if ag.get('id') == ag_id:
                    old = _agent_effective_model(ag, default_model, fallback_models)
                    if new_model == default_model:
                        ag.pop('model', None)
                    else:
                        ag['model'] = new_model
                    applied.append({'at': datetime.datetime.now().isoformat(), 'agentId': ag_id, 'oldModel': old, 'newModel': new_model})
                    found = True
                    break
            if not found:
                errors.append({'change': change, 'error': f'agent {ag_id} not found'})

        if applied:
            # 只有内容真正变化时才备份和写入
            new_cfg = dict(cfg)
            new_cfg['agents'] = dict(cfg.get('agents', {}))
            new_cfg['agents']['list'] = [dict(agent) for agent in agents_list]
            new_text = json.dumps(new_cfg, ensure_ascii=False, sort_keys=True)
            if old_cfg_text == new_text and applied:
                for item in applied:
                    item['writeSkipped'] = True
            bak = None
            if old_cfg_text != new_text:
                bak = OPENCLAW_CFG.parent / f'openclaw.json.bak.model-{datetime.datetime.now().strftime("%Y%m%d-%H%M%S")}'
                shutil.copy2(OPENCLAW_CFG, bak)
                cleanup_backups()
                atomic_json_write(OPENCLAW_CFG, new_cfg)

            log_data = rj(CHANGE_LOG, [])
            if not isinstance(log_data, list):
                log_data = []
            log_data.extend(applied)
            if len(log_data) > 200:
                log_data = log_data[-200:]
            atomic_json_write(CHANGE_LOG, log_data)

            for e in applied:
                log.info(f'{e["agentId"]}: {e["oldModel"]} → {e["newModel"]}')

            restart_ok = False
            rollback = False
            try:
                r = subprocess.run(['openclaw', 'gateway', 'restart'], capture_output=True, text=True, timeout=GATEWAY_RESTART_TIMEOUT)
                restart_ok = r.returncode == 0
                log.info(f'gateway restart rc={r.returncode}')
            except Exception as e:
                log.error(f'gateway restart failed: {e}')
                if bak and bak.exists():
                    shutil.copy2(bak, OPENCLAW_CFG)
                    log.warning('rolled back openclaw.json from backup')
                    rollback = True
                    for a in applied:
                        a['rolledBack'] = True

            atomic_json_write(PENDING, [])
            atomic_json_write(DATA / 'last_model_change_result.json', {
                'at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'applied': applied,
                'errors': errors,
                'gatewayRestarted': restart_ok,
                'rolledBack': rollback,
            })
        elif errors:
            log.warning(f'{len(errors)} changes failed, 0 applied')
            atomic_json_write(PENDING, [])
    finally:
        _release_apply_lock(lock_fd)


if __name__ == '__main__':
    main()
