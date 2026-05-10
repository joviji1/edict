#!/usr/bin/env python3
"""Evolver-equivalent analysis script.

Periodically analyzes failure patterns from:
1. verification-ledger.json (DIAGNOSED/FAIL entries)
2. Session transcripts (prompt-error patterns)
3. feature-status.json (risks & next_actions)
4. RELIABILITY.md known issues registry

Outputs a structured JSON report with:
  - failure_patterns:  list of {pattern, count, severity, status}
  - useful_suggestions: suggestions proven valuable
  - useless_suggestions: platitudes / not actionable
  - next_actions: prioritized action items

Usage:
    python3 scripts/evolver_analysis.py [--json]
    python3 scripts/evolver_analysis.py --json > /tmp/evolver-report.json

Designed to be run via cron (e.g. daily or every 6h).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from collections import Counter, defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# paths
# ---------------------------------------------------------------------------
EDICT_ROOT = Path(os.environ.get('EDICT_ROOT', '/root/.openclaw/workspace/edict'))
OPENCLAW_HOME = Path(os.environ.get('OPENCLAW_HOME', '/root/.openclaw'))
AGENTS_ROOT = OPENCLAW_HOME / 'agents'

LEDGER_PATH = EDICT_ROOT / 'docs' / 'state' / 'verification-ledger.json'
FEATURE_STATUS_PATH = EDICT_ROOT / 'docs' / 'state' / 'feature-status.json'
RELIABILITY_PATH = EDICT_ROOT / 'docs' / 'RELIABILITY.md'

# Default agents to scan for session errors
DEFAULT_AGENTS = ['taizi', 'zhongshu', 'menxia', 'shangshu']

# Error patterns to search for in transcripts (last N entries)
TRANSCRIPT_SCAN_ENTRIES = 5

# Known error message patterns (regex) -> canonical pattern name
KNOWN_ERROR_PATTERNS = [
    (r'524\s*status\s*code',              'upstream_524_timeout'),
    (r'401.*(?:invalid|token|key)',       'api_key_invalid_401'),
    (r'401.*unauthorized',               'api_key_invalid_401'),
    (r'lane\s*wait\s*exceeded',           'session_lane_wait_timeout'),
    (r'orphaned\s*user\s*message',        'orphaned_user_messages'),
    (r'consecutive\s*user\s*turns',       'consecutive_user_turns_dirty'),
    (r'too\s*many\s*requests',            'rate_limit_429'),
    (r'context\s*length\s*exceeded',      'context_window_overflow'),
    (r'ECONNREFUSED',                     'connection_refused'),
    (r'ENOTFOUND',                        'dns_resolution_failure'),
    (r'fallback.*false',                  'no_fallback_configured'),
    (r'stopReason.*error',                'model_stop_error'),
    (r'(?i)^aborted$',                    'session_aborted'),
]


# ===================================================================
#  1. verification-ledger analysis
# ===================================================================

def load_json(path: Path, default=None):
    """Safe JSON load."""
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return default if default is not None else {}


def analyze_ledger(ledger: dict) -> dict:
    """Extract failure / diagnosis entries from the verification ledger."""
    entries = ledger.get('entries', [])

    failed = []
    diagnosed = []
    passed_count = 0
    passed_with_notes_count = 0

    for e in entries:
        # Ledger uses two schemas: old-style 'result' and new-style 'status'
        result = (e.get('result') or e.get('status') or '').upper()
        if result in ('FAIL', 'FAILED'):
            failed.append(e)
        elif result in ('DIAGNOSED',):
            diagnosed.append(e)
        elif result in ('PASS', 'PASSED'):
            passed_count += 1
        elif result in ('PASSED_WITH_NOTES', 'PASSED WITH NOTES'):
            passed_with_notes_count += 1

    # Build failure pattern list from diagnosed entries
    patterns = []
    pattern_counter = Counter()

    for e in diagnosed:
        action = e.get('action', e.get('summary', ''))
        evidence = e.get('evidence', {})
        # Extract a concise pattern name from action + evidence
        if isinstance(evidence, dict):
            conclusion = evidence.get('conclusion', '')
        else:
            conclusion = ''
        pattern_key = conclusion or action
        pattern_counter[pattern_key] += 1

    for e in failed:
        action = e.get('action', e.get('summary', ''))
        pattern_counter[action] += 1

    for pattern_text, count in pattern_counter.items():
        patterns.append({
            'pattern': pattern_text[:200],
            'count': count,
            'severity': 'high' if count > 1 else 'medium',
            'status': 'active' if count > 0 else 'resolved',
        })

    return {
        'total_entries': len(entries),
        'passed': passed_count,
        'passed_with_notes': passed_with_notes_count,
        'diagnosed': len(diagnosed),
        'failed': len(failed),
        'failure_patterns_from_ledger': patterns,
        'raw_diagnosed': [_simplify_entry(e) for e in diagnosed],
        'raw_failed': [_simplify_entry(e) for e in failed],
    }


def _simplify_entry(entry: dict) -> dict:
    """Return a slimmed-down version of a ledger entry."""
    return {
        'entry_id': entry.get('entry_id', ''),
        'feature_id': entry.get('feature_id', ''),
        'action': entry.get('action', entry.get('summary', '')),
        'result': entry.get('result', entry.get('status', '')),
        'notes': entry.get('notes', []),
    }


# ===================================================================
#  2. Session transcript analysis
# ===================================================================

def load_sessions(agent_id: str) -> dict:
    """Load sessions.json for an agent."""
    path = AGENTS_ROOT / agent_id / 'sessions' / 'sessions.json'
    return load_json(path, default={})


def get_last_entries(session_file: Path, n: int = TRANSCRIPT_SCAN_ENTRIES) -> list:
    """Read the last N JSONL entries from a transcript file."""
    if not session_file.exists() or not session_file.is_file():
        return []
    lines = []
    try:
        with session_file.open('rb') as f:
            f.seek(0, 2)
            size = f.tell()
            read_start = max(0, size - 131072)  # read last 128KB
            f.seek(read_start)
            data = f.read().decode('utf-8', 'replace')
            all_lines = data.strip().split('\n')
            start = 1 if read_start > 0 and len(all_lines) > 1 else 0
            lines = all_lines[start:]
    except Exception:
        return []

    entries = []
    for line in lines[-n:]:
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return entries


def scan_transcripts(agent_ids: list) -> dict:
    """Scan session transcripts for error patterns."""
    error_counter = Counter()
    error_details = []  # list of {agent, session_key, error_type, message, provider, model}
    total_sessions = 0
    sessions_with_errors = 0

    for agent_id in agent_ids:
        sessions = load_sessions(agent_id)
        for key, entry in sessions.items():
            if not isinstance(entry, dict):
                continue
            total_sessions += 1

            session_file = Path(entry.get('sessionFile', ''))
            if not session_file.exists() or not session_file.is_file():
                continue

            last_entries = get_last_entries(session_file)
            session_had_error = False

            for record in last_entries:
                # Check for openclaw:prompt-error custom type
                if (record.get('type') == 'custom'
                        and record.get('customType') == 'openclaw:prompt-error'):
                    err_data = record.get('data', {})
                    err_msg = err_data.get('error', 'unknown')
                    provider = err_data.get('provider', '?')
                    model = err_data.get('model', '?')

                    canonical = _match_error_pattern(err_msg)
                    error_counter[canonical] += 1
                    session_had_error = True
                    error_details.append({
                        'agent': agent_id,
                        'session_key': key[:60],
                        'error_type': canonical,
                        'message': err_msg[:200],
                        'provider': provider,
                        'model': model,
                    })

                # Also check for stopReason=error in assistant messages
                if (record.get('type') == 'assistant'
                        and record.get('stopReason') == 'error'):
                    err_msg = record.get('errorMessage', 'unknown')
                    canonical = _match_error_pattern(err_msg)
                    error_counter[canonical] += 1
                    session_had_error = True
                    error_details.append({
                        'agent': agent_id,
                        'session_key': key[:60],
                        'error_type': canonical,
                        'message': err_msg[:200],
                    })

            if session_had_error:
                sessions_with_errors += 1

    # Deduplicate error_details by (agent, session_key, error_type) to avoid noise
    seen = set()
    unique_details = []
    for d in error_details:
        k = (d['agent'], d['session_key'], d['error_type'])
        if k not in seen:
            seen.add(k)
            unique_details.append(d)

    return {
        'total_sessions_scanned': total_sessions,
        'sessions_with_errors': sessions_with_errors,
        'error_type_counts': dict(error_counter.most_common()),
        'error_details': unique_details[:30],  # cap output
    }


def _match_error_pattern(error_msg: str) -> str:
    """Match an error message against known patterns, return canonical name."""
    for regex, canonical in KNOWN_ERROR_PATTERNS:
        if re.search(regex, error_msg, re.IGNORECASE):
            return canonical
    return 'unknown_error'


# ===================================================================
#  3. Feature status & risks
# ===================================================================

def analyze_features(feature_status: dict) -> dict:
    """Collect risks and next actions from feature-status.json."""
    features = feature_status.get('features', [])
    all_risks = []
    all_next_actions = []

    for f in features:
        fid = f.get('feature_id', '?')
        title = f.get('title', '?')
        status = f.get('status', '?')

        for risk in f.get('risks', []):
            all_risks.append({
                'feature_id': fid,
                'feature_title': title,
                'feature_status': status,
                'risk': risk,
            })

        na = f.get('next_action', '')
        if na:
            all_next_actions.append({
                'feature_id': fid,
                'feature_title': title,
                'action': na,
            })

    return {
        'features_total': len(features),
        'risks': all_risks,
        'next_actions': all_next_actions,
    }


# ===================================================================
#  4. RELIABILITY.md known-issues extraction
# ===================================================================

def parse_known_issues() -> list:
    """Parse RELIABILITY.md §5 for known issues."""
    if not RELIABILITY_PATH.exists():
        return []

    text = RELIABILITY_PATH.read_text(encoding='utf-8')
    issues = []

    # Match ### 5.N sections
    pattern = re.compile(
        r'###\s+5\.\d+\s+.*?[⚠️ℹ️❌]?\s*(.*?)\n(.*?)(?=###\s+5\.\d+|##\s+\d|\Z)',
        re.DOTALL
    )
    for m in pattern.finditer(text):
        title = m.group(1).strip()
        body = m.group(2).strip()
        # Extract fields
        phenomenon = _extract_md_field(body, '现象')
        root_cause = _extract_md_field(body, '根因')
        impact = _extract_md_field(body, '影响范围') or _extract_md_field(body, '影响')
        status = _extract_md_field(body, '状态')
        countermeasure = _extract_md_field(body, '对策') or _extract_md_field(body, '临时对策')

        severity = 'high' if '⚠️' in title else 'info'
        issues.append({
            'title': title,
            'phenomenon': phenomenon,
            'root_cause': root_cause,
            'impact': impact,
            'status': status,
            'countermeasure': countermeasure,
            'severity': severity,
        })

    return issues


def _extract_md_field(text: str, field_name: str) -> str:
    """Extract a '- **field**: value' line from markdown text."""
    m = re.search(rf'\*\*{re.escape(field_name)}\*\*:\s*(.+)', text)
    return m.group(1).strip() if m else ''


# ===================================================================
#  5. Synthesis: suggestions & actions
# ===================================================================

def synthesize_report(ledger_analysis: dict,
                      transcript_analysis: dict,
                      feature_analysis: dict,
                      known_issues: list) -> dict:
    """Merge all analyses into the final Evolver-equivalent report."""

    # -- failure_patterns: merge ledger + transcript + known issues --
    patterns = []

    # From ledger diagnosed/failed
    for p in ledger_analysis.get('failure_patterns_from_ledger', []):
        patterns.append({
            'pattern': p['pattern'],
            'count': p['count'],
            'severity': p['severity'],
            'status': p['status'],
            'source': 'verification-ledger',
        })

    # From transcript error types
    for error_type, count in transcript_analysis.get('error_type_counts', {}).items():
        # Skip if already captured by ledger
        already = any(p['pattern'] == error_type for p in patterns)
        if not already:
            severity = 'high' if count >= 3 else 'medium' if count >= 1 else 'low'
            patterns.append({
                'pattern': error_type,
                'count': count,
                'severity': severity,
                'status': 'active',
                'source': 'session-transcripts',
            })

    # From known issues in RELIABILITY.md
    for ki in known_issues:
        already = any(ki['title'] in p['pattern'] for p in patterns)
        if not already:
            patterns.append({
                'pattern': ki['title'],
                'count': 1,
                'severity': ki['severity'],
                'status': ki.get('status', 'known'),
                'source': 'RELIABILITY.md',
            })

    # -- useful_suggestions --
    # Heuristics: suggestions that led to real action or resolution
    useful = []

    # Check ledger entries that have concrete evidence of improvement
    for entry in (ledger_analysis.get('raw_diagnosed', []) +
                  ledger_analysis.get('raw_failed', [])):
        notes = entry.get('notes', [])
        if isinstance(notes, str):
            notes = [notes]
        for note in notes:
            if any(kw in note for kw in ['已修正', '已修复', '已降级', '已收紧', '修正为']):
                useful.append({
                    'suggestion': note[:200],
                    'evidence': entry.get('action', ''),
                    'source': 'verification-ledger',
                })

    # From known issues with countermeasures
    for ki in known_issues:
        if ki.get('countermeasure'):
            useful.append({
                'suggestion': ki['countermeasure'],
                'evidence': ki.get('phenomenon', ''),
                'source': 'RELIABILITY.md',
            })

    # -- useless_suggestions --
    # Patterns that indicate platitude-level output
    PLATITUDE_KEYWORDS = [
        '继续观察', '需要持续', '待定', '后续再补',
        'observe', 'monitor', 'todo', 'tbd',
    ]
    useless = []
    for entry in (ledger_analysis.get('raw_diagnosed', []) +
                  ledger_analysis.get('raw_failed', [])):
        notes = entry.get('notes', [])
        if isinstance(notes, str):
            notes = [notes]
        for note in notes:
            if any(kw in note.lower() for kw in PLATITUDE_KEYWORDS):
                # Only mark as useless if there's no accompanying action
                if not any(kw in note for kw in ['已', '完成', 'done', 'fixed']):
                    useless.append({
                        'suggestion': note[:200],
                        'reason': '未附带具体行动项或执行证据',
                        'source': 'verification-ledger',
                    })

    # -- next_actions: prioritize from feature-status + patterns --
    next_actions = []

    # High severity unresolved patterns
    for p in patterns:
        if p['severity'] == 'high' and p['status'] in ('active', 'known'):
            next_actions.append({
                'priority': 1,
                'action': f"解决高危故障模式: {p['pattern'][:100]}",
                'source': p.get('source', 'analysis'),
                'category': 'failure_resolution',
            })

    # Feature next_actions (medium priority)
    for na in feature_analysis.get('next_actions', []):
        next_actions.append({
            'priority': 2,
            'action': f"[{na['feature_id']}] {na['action']}",
            'source': 'feature-status',
            'category': 'feature_progress',
        })

    # Risk mitigation (medium-low)
    for risk in feature_analysis.get('risks', []):
        next_actions.append({
            'priority': 3,
            'action': f"缓解风险 [{risk['feature_id']}]: {risk['risk']}",
            'source': 'feature-status',
            'category': 'risk_mitigation',
        })

    # Sort by priority
    next_actions.sort(key=lambda x: x['priority'])

    # -- assemble report --
    report = {
        'report_type': 'evolver_equivalent_analysis',
        'generated_at': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
        'schema_version': '1.0',
        'summary': {
            'total_failure_patterns': len(patterns),
            'high_severity': sum(1 for p in patterns if p['severity'] == 'high'),
            'medium_severity': sum(1 for p in patterns if p['severity'] == 'medium'),
            'useful_suggestions_count': len(useful),
            'useless_suggestions_count': len(useless),
            'next_actions_count': len(next_actions),
            'features_tracked': feature_analysis.get('features_total', 0),
            'sessions_scanned': transcript_analysis.get('total_sessions_scanned', 0),
            'sessions_with_errors': transcript_analysis.get('sessions_with_errors', 0),
        },
        'failure_patterns': patterns,
        'useful_suggestions': useful,
        'useless_suggestions': useless,
        'next_actions': next_actions,
        'raw': {
            'ledger': ledger_analysis,
            'transcripts': transcript_analysis,
            'features': feature_analysis,
            'known_issues': known_issues,
        },
    }

    return report


# ===================================================================
#  6. Human-readable output
# ===================================================================

def print_human_report(report: dict):
    """Print a concise human-readable summary."""
    s = report['summary']
    print("=" * 60)
    print("  EVOLVER-EQUIVALENT ANALYSIS REPORT")
    print(f"  Generated: {report['generated_at']}")
    print("=" * 60)
    print()
    print(f"  Features tracked:       {s['features_tracked']}")
    print(f"  Sessions scanned:       {s['sessions_scanned']}")
    print(f"  Sessions with errors:   {s['sessions_with_errors']}")
    print()
    print("--- FAILURE PATTERNS ---")
    print(f"  Total:    {s['total_failure_patterns']}")
    print(f"  High:     {s['high_severity']}")
    print(f"  Medium:   {s['medium_severity']}")
    print()
    for p in report['failure_patterns']:
        icon = '🔴' if p['severity'] == 'high' else '🟡' if p['severity'] == 'medium' else '⚪'
        print(f"  {icon} [{p['severity']}] {p['pattern'][:80]} (x{p['count']}) [{p.get('source','')}]")
    print()
    print("--- USEFUL SUGGESTIONS ---")
    print(f"  Count: {s['useful_suggestions_count']}")
    for u in report['useful_suggestions'][:10]:
        print(f"  ✅ {u['suggestion'][:100]}")
    print()
    print("--- USELESS SUGGESTIONS (platitudes) ---")
    print(f"  Count: {s['useless_suggestions_count']}")
    for u in report['useless_suggestions'][:10]:
        print(f"  ❌ {u['suggestion'][:100]}")
        print(f"     Reason: {u['reason']}")
    print()
    print("--- NEXT ACTIONS (prioritized) ---")
    for i, a in enumerate(report['next_actions'][:15], 1):
        prio_icon = '🔴' if a['priority'] == 1 else '🟡' if a['priority'] == 2 else '🟢'
        print(f"  {prio_icon} P{a['priority']} #{i}: {a['action'][:100]}")
    print()
    print("=" * 60)


# ===================================================================
#  main
# ===================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Evolver-equivalent failure pattern analysis')
    parser.add_argument('--json', action='store_true',
                        help='Output raw JSON (for piping / cron)')
    parser.add_argument('--agents', nargs='+', default=DEFAULT_AGENTS,
                        help='Agent IDs to scan (default: taizi zhongshu menxia shangshu)')
    parser.add_argument('--output', '-o', type=str, default=None,
                        help='Write JSON report to file')
    args = parser.parse_args()

    # 1. Load & analyze verification ledger
    ledger = load_json(LEDGER_PATH, default={'entries': []})
    ledger_analysis = analyze_ledger(ledger)

    # 2. Scan session transcripts
    transcript_analysis = scan_transcripts(args.agents)

    # 3. Load & analyze feature status
    feature_status = load_json(FEATURE_STATUS_PATH, default={'features': []})
    feature_analysis = analyze_features(feature_status)

    # 4. Parse known issues from RELIABILITY.md
    known_issues = parse_known_issues()

    # 5. Synthesize
    report = synthesize_report(ledger_analysis, transcript_analysis,
                               feature_analysis, known_issues)

    # 6. Output
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                            encoding='utf-8')
        print(f"Report written to {out_path}")

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_human_report(report)

    # Exit code: 0 if no high-severity issues, 1 otherwise
    return 1 if report['summary']['high_severity'] > 0 else 0


if __name__ == '__main__':
    exit(main())
