import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    'guard_openclaw_sessions',
    '/root/.openclaw/workspace/edict/scripts/guard_openclaw_sessions.py',
)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def test_detect_entry_issues_flags_mismatch_overflow_and_context_warning(tmp_path):
    sessions_dir = tmp_path / 'sessions'
    sessions_dir.mkdir()
    transcript = sessions_dir / 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb.jsonl'
    transcript.write_text(
        "The input (221512 tokens) is longer than the model's context length (131072 tokens).",
        encoding='utf-8',
    )
    cfg = {
        'models': {
            'providers': {
                'longcat': {'models': [{'id': 'LongCat-Flash-Chat', 'contextWindow': 131072}]}
            }
        },
        'agents': {'defaults': {'model': {'primary': 'longcat/LongCat-Flash-Chat'}}},
    }
    windows = mod.build_model_windows(cfg)
    entry = {
        'sessionId': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        'sessionFile': str(transcript),
        'status': 'failed',
        'contextTokens': 200000,
        'modelProvider': 'longcat',
        'model': 'LongCat-Flash-Chat',
    }
    issue = mod.detect_entry_issues('agent:zhongshu:main', entry, cfg, windows, sessions_dir, True)
    assert issue is not None
    assert 'session_id_file_mismatch' in issue['reasons']
    assert 'transcript_context_overflow' in issue['reasons']
    assert issue['contextWindowWarning'].startswith('200000>131072:longcat/LongCat-Flash-Chat')


def test_detect_entry_issues_flags_stale_context_window_metadata(tmp_path):
    sessions_dir = tmp_path / 'sessions'
    sessions_dir.mkdir()
    transcript = sessions_dir / 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa.jsonl'
    transcript.write_text('ok', encoding='utf-8')
    cfg = {
        'models': {
            'providers': {
                'longcat': {'models': [{'id': 'LongCat-Flash-Chat', 'contextWindow': 256000}]}
            }
        },
        'agents': {'defaults': {'model': {'primary': 'longcat/LongCat-Flash-Chat'}}},
    }
    windows = mod.build_model_windows(cfg)
    entry = {
        'sessionId': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        'sessionFile': str(transcript),
        'contextTokens': 131072,
        'modelProvider': 'longcat',
        'model': 'LongCat-Flash-Chat',
    }
    issue = mod.detect_entry_issues('agent:taizi:main', entry, cfg, windows, sessions_dir, True)
    assert issue is not None
    assert 'stale_context_window_metadata' in issue['reasons']
    assert issue['contextWindowWarning'].startswith('131072<256000:longcat/LongCat-Flash-Chat')


def test_detect_entry_issues_flags_missing_transcript_for_main_session(tmp_path):
    sessions_dir = tmp_path / 'sessions'
    sessions_dir.mkdir()
    missing = sessions_dir / 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa.jsonl'
    cfg = {'models': {'providers': {}}, 'agents': {'defaults': {'model': {}}}}
    windows = mod.build_model_windows(cfg)
    entry = {
        'sessionId': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        'sessionFile': str(missing),
    }
    issue = mod.detect_entry_issues('agent:shangshu:main', entry, cfg, windows, sessions_dir, True)
    assert issue is not None
    assert 'missing_transcript_file' in issue['reasons']



def test_rotate_entry_creates_new_session_file_and_clears_runtime_fields(tmp_path):
    sessions_dir = tmp_path / 'sessions'
    sessions_dir.mkdir()
    entry = {
        'sessionId': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        'sessionFile': str(sessions_dir / 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa.jsonl'),
        'modelProvider': 'longcat',
        'model': 'LongCat-Flash-Chat',
        'inputTokens': 1,
        'outputTokens': 2,
        'totalTokens': 3,
        'contextTokens': 4,
    }
    rotated = mod.rotate_entry(entry, sessions_dir)
    assert rotated['sessionId'] != entry['sessionId']
    assert Path(rotated['sessionFile']).stem == rotated['sessionId']
    assert Path(rotated['sessionFile']).exists()
    assert rotated['totalTokensFresh'] is False
    for field in ['modelProvider', 'model', 'inputTokens', 'outputTokens', 'totalTokens', 'contextTokens']:
        assert field not in rotated
