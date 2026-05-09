from pathlib import Path


DOCTOR = Path('/root/.openclaw/workspace/edict/scripts/doctor_edict.sh')


def test_doctor_edict_includes_openclaw_feishu_p2p_guard_probe():
    text = DOCTOR.read_text(encoding='utf-8')

    assert 'check_openclaw_feishu_guard' in text
    assert 'check_openclaw_feishu_guard "$GUARD_SCRIPT"' in text
    assert 'check_openclaw_feishu_p2p_guard.py' in text
