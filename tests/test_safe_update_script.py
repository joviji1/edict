import json
import os
import pathlib
import subprocess

ROOT = pathlib.Path('/root/.openclaw/workspace/edict')
SCRIPT = ROOT / 'scripts' / 'safe_update.sh'


def run_safe(mode, run_dir=None, env=None):
    cmd = ['bash', str(SCRIPT), mode]
    if run_dir:
        cmd.append(str(run_dir))
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, env=merged)


def test_plan_generates_plan_file(tmp_path):
    env = {'EDICT_BACKUP_ROOT': str(tmp_path)}
    res = run_safe('plan', env=env)
    assert res.returncode == 0, res.stderr
    plan_files = list(tmp_path.glob('safe-update-*/plan.json'))
    assert len(plan_files) == 1
    payload = json.loads(plan_files[0].read_text(encoding='utf-8'))
    assert payload['policy'].startswith('No service restart')
    assert any(s['name'] == 'restart' for s in payload['stages'])


def test_prepare_backs_up_data_without_restart(tmp_path):
    env = {'EDICT_BACKUP_ROOT': str(tmp_path)}
    res = run_safe('prepare', env=env)
    assert res.returncode == 0, res.stderr
    run_dirs = list(tmp_path.glob('safe-update-*'))
    assert run_dirs, 'prepare should create a run dir'
    run_dir = run_dirs[0]
    assert (run_dir / 'plan.json').exists()
    assert (run_dir / 'git-status.txt').exists()
    assert (run_dir / 'data').exists()
    assert (run_dir / 'memory').exists()
    assert (run_dir / 'memory' / 'data' / 'tasks_source.json').exists()
    log_text = (run_dir / 'safe_update.log').read_text(encoding='utf-8')
    assert '已备份' in log_text or '跳过备份' in log_text
    assert 'restart 阶段完成' not in log_text


def test_rollback_requires_explicit_confirmation(tmp_path):
    env = {'EDICT_BACKUP_ROOT': str(tmp_path)}
    prep = run_safe('prepare', env=env)
    assert prep.returncode == 0, prep.stderr
    run_dir = next(tmp_path.glob('safe-update-*'))
    res = run_safe('rollback', run_dir=run_dir)
    assert res.returncode != 0
    assert 'CONFIRM_ROLLBACK_EDICT' in (res.stdout + res.stderr)


def test_restart_requires_explicit_confirmation(tmp_path):
    env = {'EDICT_BACKUP_ROOT': str(tmp_path)}
    prep = run_safe('prepare', env=env)
    assert prep.returncode == 0, prep.stderr
    run_dir = next(tmp_path.glob('safe-update-*'))
    res = run_safe('restart', run_dir=run_dir)
    assert res.returncode != 0
    assert 'CONFIRM_RESTART_EDICT' in (res.stdout + res.stderr)
