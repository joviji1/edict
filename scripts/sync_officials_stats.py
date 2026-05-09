#!/usr/bin/env python3
"""同步各官员统计数据 → data/officials_stats.json"""
import json, pathlib, datetime, logging
from file_lock import atomic_json_write
from utils import get_openclaw_home

log = logging.getLogger('officials')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(message)s', datefmt='%H:%M:%S')

BASE = pathlib.Path(__file__).resolve().parent.parent
DATA = BASE / 'data'
OPENCLAW_HOME = get_openclaw_home()
AGENTS_ROOT = OPENCLAW_HOME / 'agents'
OPENCLAW_CFG = OPENCLAW_HOME / 'openclaw.json'

# Anthropic 定价（每1M token，美元）
MODEL_PRICING = {
    'anthropic/claude-sonnet-4-6':  {'in':3.0, 'out':15.0, 'cr':0.30, 'cw':3.75},
    'anthropic/claude-opus-4-5':    {'in':15.0,'out':75.0, 'cr':1.50, 'cw':18.75},
    'anthropic/claude-haiku-3-5':   {'in':0.8, 'out':4.0,  'cr':0.08, 'cw':1.0},
    'openai/gpt-4o':                {'in':2.5, 'out':10.0, 'cr':1.25, 'cw':0},
    'openai/gpt-4o-mini':           {'in':0.15,'out':0.6,  'cr':0.075,'cw':0},
    'google/gemini-2.0-flash':      {'in':0.075,'out':0.3, 'cr':0,    'cw':0},
    'google/gemini-2.5-pro':        {'in':1.25,'out':10.0, 'cr':0,    'cw':0},
}

OFFICIALS = [
    {'id':'taizi',   'label':'太子',  'role':'太子',    'emoji':'🤴','rank':'储君'},
    {'id':'zhongshu','label':'中书省','role':'中书令',  'emoji':'📜','rank':'正一品'},
    {'id':'menxia',  'label':'门下省','role':'侍中',    'emoji':'🔍','rank':'正一品'},
    {'id':'shangshu','label':'尚书省','role':'尚书令',  'emoji':'📮','rank':'正一品'},
    {'id':'libu',    'label':'礼部',  'role':'礼部尚书','emoji':'📝','rank':'正二品'},
    {'id':'hubu',    'label':'户部',  'role':'户部尚书','emoji':'💰','rank':'正二品'},
    {'id':'bingbu',  'label':'兵部',  'role':'兵部尚书','emoji':'⚔️','rank':'正二品'},
    {'id':'xingbu',  'label':'刑部',  'role':'刑部尚书','emoji':'⚖️','rank':'正二品'},
    {'id':'gongbu',  'label':'工部',  'role':'工部尚书','emoji':'🔧','rank':'正二品'},
    {'id':'libu_hr', 'label':'吏部',  'role':'吏部尚书','emoji':'👔','rank':'正二品'},
    {'id':'zaochao', 'label':'钦天监','role':'朝报官',  'emoji':'📰','rank':'正三品'},
]

def rj(p, d):
    try:
        return json.loads(pathlib.Path(p).read_text(encoding='utf-8'))
    except Exception:
        return d


# Pre-load openclaw config once (avoid re-reading per agent)
_OPENCLAW_CACHE = None

def _load_openclaw_cfg():
    global _OPENCLAW_CACHE
    if _OPENCLAW_CACHE is None:
        _OPENCLAW_CACHE = rj(OPENCLAW_CFG, {})
    return _OPENCLAW_CACHE


def normalize_model(model_value, fallback='anthropic/claude-sonnet-4-6'):
    if isinstance(model_value, str) and model_value:
        return model_value
    if isinstance(model_value, dict):
        return model_value.get('primary') or model_value.get('id') or fallback
    return fallback

def get_model(agent_id):
    cfg = _load_openclaw_cfg()
    default = normalize_model(cfg.get('agents',{}).get('defaults',{}).get('model',{}), 'anthropic/claude-sonnet-4-6')
    for a in cfg.get('agents',{}).get('list',[]):
        if a.get('id') == agent_id:
            return normalize_model(a.get('model', default), default)
    # 兼容历史：太子曾使用 main 作为运行时 id
    if agent_id == 'taizi':
        for a in cfg.get('agents',{}).get('list',[]):
            if a.get('id') == 'main':
                return normalize_model(a.get('model', default), default)
    return default

def scan_agent(agent_id):
    """从 sessions.json 读取 token 统计（累计所有 session）"""
    sj = AGENTS_ROOT / agent_id / 'sessions' / 'sessions.json'
    if not sj.exists() and agent_id == 'taizi':
        sj = AGENTS_ROOT / 'main' / 'sessions' / 'sessions.json'
    if not sj.exists():
        return {'tokens_in':0,'tokens_out':0,'cache_read':0,'cache_write':0,'sessions':0,'last_active':None,'messages':0}
    
    data = rj(sj, {})
    tin = tout = cr = cw = 0
    last_ts = None
    
    for sid, v in data.items():
        tin += v.get('inputTokens', 0) or 0
        tout += v.get('outputTokens', 0) or 0
        cr  += v.get('cacheRead', 0) or 0
        cw  += v.get('cacheWrite', 0) or 0
        ts = v.get('updatedAt')
        if ts:
            try:
                t = datetime.datetime.fromtimestamp(ts/1000) if isinstance(ts,int) else datetime.datetime.fromisoformat(ts.replace('Z','+00:00'))
                if last_ts is None or t > last_ts: last_ts = t
            except Exception: pass
    
    # Estimate message count from most recent session JSONL
    msg_count = 0
    if data:
        try:
            sf_key = max(data.keys(), key=lambda k: data[k].get('updatedAt',0) or 0, default=None)
        except Exception:
            sf_key = None
    else:
        sf_key = None
    if sf_key and data[sf_key].get('sessionFile'):
        sf = AGENTS_ROOT / agent_id / 'sessions' / pathlib.Path(data[sf_key]['sessionFile']).name
        try:
            lines = sf.read_text(errors='ignore').splitlines()
            for ln in lines:
                try:
                    e = json.loads(ln)
                    if e.get('type') == 'message' and e.get('message',{}).get('role') == 'assistant':
                        msg_count += 1
                except Exception: pass
        except Exception: pass

    return {
        'tokens_in': tin, 'tokens_out': tout,
        'cache_read': cr, 'cache_write': cw,
        'sessions': len(data),
        'last_active': last_ts.strftime('%Y-%m-%d %H:%M') if last_ts else None,
        'messages': msg_count,
    }

def calc_cost(s, model):
    p = MODEL_PRICING.get(model, MODEL_PRICING['anthropic/claude-sonnet-4-6'])
    usd = (s['tokens_in']/1e6*p['in'] + s['tokens_out']/1e6*p['out']
         + s['cache_read']/1e6*p['cr'] + s['cache_write']/1e6*p['cw'])
    return round(usd, 4)

def get_task_stats(org_label, tasks):
    owned = [t for t in tasks if t.get('org') == org_label]
    done = [t for t in owned if t.get('state') == 'Done']
    blocked = [t for t in owned if t.get('state') == 'Blocked']
    active = [t for t in owned if t.get('state') in ('Doing', 'Review', 'Assigned')]
    fl = sum(1 for t in tasks for f in t.get('flow_log', [])
             if f.get('from') == org_label or f.get('to') == org_label)

    participated = []
    for t in tasks:
        if not t['id'].startswith('JJC'):
            continue
        for f in t.get('flow_log', []):
            if f.get('from') == org_label or f.get('to') == org_label:
                if t['id'] not in [x['id'] for x in participated]:
                    participated.append({'id': t['id'], 'title': t.get('title', ''), 'state': t.get('state', '')})
                break

    timeout_count = 0
    scheduler_retries = 0
    task_tokens = 0
    task_cost_usd = 0.0
    task_elapsed_sec = 0
    merit_history = []
    for t in owned:
        autopsy = t.get('autopsy') or {}
        sched = t.get('_scheduler') or t.get('scheduler') or {}
        reason_parts = [
            str(t.get('block', '')).lower(),
            str(autopsy.get('reason', '')).lower(),
            str(sched.get('stallReason', '')).lower(),
        ]
        if any(k in ' '.join(reason_parts) for k in ('timeout', 'timed out', '超时')):
            timeout_count += 1
        scheduler_retries += int(sched.get('retryCount') or 0)
        for log in t.get('progress_log', []) or []:
            task_tokens += int(log.get('tokens') or 0)
            task_cost_usd += float(log.get('cost') or 0.0)
            task_elapsed_sec += int(log.get('elapsed') or 0)

        merit_delta = 0
        if t.get('state') == 'Done':
            merit_delta += 10
        elif t.get('state') == 'Blocked':
            merit_delta -= 4
        merit_delta -= int(sched.get('retryCount') or 0)
        if any(k in ' '.join(reason_parts) for k in ('timeout', 'timed out', '超时')):
            merit_delta -= 2
        if t.get('state') in ('Doing', 'Review', 'Assigned'):
            merit_delta += 2
        merit_history.append({
            'task_id': t.get('id', ''),
            'score': merit_delta,
            'state': t.get('state', ''),
        })

    terminal = len(done) + len(blocked)
    success_rate = round(len(done) / terminal, 4) if terminal else 0.0
    timeout_rate = round(timeout_count / len(owned), 4) if owned else 0.0
    sla_score = max(0, len(done) * 20 - len(blocked) * 4 - timeout_count * 2 - scheduler_retries + len(active) * 2)
    productivity = success_rate * 100 + len(done) * 5 + max(0, len(active))
    stability = max(0.0, 100 - timeout_count * 20 - scheduler_retries * 5 - len(blocked) * 10)
    efficiency = max(0.0, 100 - task_elapsed_sec / 30 - task_cost_usd * 50)
    composite_score = round(productivity * 0.45 + stability * 0.35 + efficiency * 0.20 + timeout_count * (2.3 if len(active) else 1.25), 2)

    return {
        'tasks_done': len(done),
        'tasks_blocked': len(blocked),
        'tasks_active': len(active),
        'tasks_total': len(owned),
        'flow_participations': fl,
        'participated_edicts': participated,
        'success_rate': success_rate,
        'timeout_count': timeout_count,
        'timeout_rate': timeout_rate,
        'scheduler_retries': scheduler_retries,
        'task_tokens': task_tokens,
        'task_cost_usd': round(task_cost_usd, 4),
        'task_elapsed_sec': task_elapsed_sec,
        'sla_score': sla_score,
        'productivity_score': round(productivity, 2),
        'stability_score': round(stability, 2),
        'efficiency_score': round(efficiency, 2),
        'composite_score': composite_score,
        'merit_history': merit_history[-8:],
    }

def get_hb(agent_id, live_tasks):
    for t in live_tasks:
        if t.get('sourceMeta',{}).get('agentId')==agent_id and t.get('heartbeat'):
            return t['heartbeat']
    return {'status':'idle','label':'⚪ 待命','ageSec':None}

def main():
    tasks = rj(DATA/'tasks_source.json', [])
    live  = rj(DATA/'live_status.json', {})
    live_tasks = live.get('tasks', [])

    result = []
    for off in OFFICIALS:
        model   = get_model(off['id'])
        ss      = scan_agent(off['id'])
        ts      = get_task_stats(off['label'], tasks)
        hb      = get_hb(off['id'], live_tasks)
        cost_usd = calc_cost(ss, model)

        result.append({
            **off,
            'model': model,
            'model_short': model.split('/')[-1] if isinstance(model, str) and '/' in model else str(model),
            'sessions': ss['sessions'],
            'tokens_in': ss['tokens_in'],
            'tokens_out': ss['tokens_out'],
            'cache_read': ss['cache_read'],
            'cache_write': ss['cache_write'],
            'tokens_total': ss['tokens_in'] + ss['tokens_out'],
            'messages': ss['messages'],
            'cost_usd': cost_usd,
            'cost_cny': round(cost_usd * 7.25, 2),
            'last_active': ss['last_active'],
            'heartbeat': hb,
            'tasks_done': ts['tasks_done'],
            'tasks_blocked': ts['tasks_blocked'],
            'tasks_active': ts['tasks_active'],
            'tasks_total': ts['tasks_total'],
            'flow_participations': ts['flow_participations'],
            'participated_edicts': ts['participated_edicts'],
            'success_rate': ts['success_rate'],
            'timeout_count': ts['timeout_count'],
            'timeout_rate': ts['timeout_rate'],
            'scheduler_retries': ts['scheduler_retries'],
            'task_tokens': ts['task_tokens'],
            'task_cost_usd': ts['task_cost_usd'],
            'task_cost_cny': round(ts['task_cost_usd'] * 7.25, 2),
            'task_elapsed_sec': ts['task_elapsed_sec'],
            'sla_score': ts['sla_score'],
            'productivity_score': ts['productivity_score'],
            'stability_score': ts['stability_score'],
            'efficiency_score': ts['efficiency_score'],
            'composite_score': ts['composite_score'],
            'merit_history': ts['merit_history'],
            'merit_score': ts['tasks_done']*10 + ts['flow_participations']*2 + min(ss['sessions'],20) + ts['sla_score'],
        })

    result.sort(key=lambda x: (x['merit_score'], x.get('composite_score', 0)), reverse=True)
    top_tier = result[:max(1, min(3, len(result)))]
    bottom_tier = result[-max(1, min(3, len(result))):] if result else []
    top_ids = {
        r['id'] for r in top_tier
        if (r.get('tasks_done', 0) > r.get('tasks_blocked', 0) and r.get('success_rate', 0) >= 0.5)
    }
    bottom_ids = {
        r['id'] for r in result
        if (r.get('tasks_blocked', 0) > 0 or r.get('timeout_count', 0) > 0)
    }
    for r in result:
        tags = []
        if r['id'] in top_ids:
            tags.append('能臣')
        if r['id'] in bottom_ids:
            tags.append('需训练')
        r['tags'] = tags
    for i, r in enumerate(result): r['merit_rank'] = i+1

    totals = {
        'tokens_total': sum(r['tokens_total'] for r in result),
        'cache_total':  sum(r['cache_read']+r['cache_write'] for r in result),
        'cost_usd':     round(sum(r['cost_usd'] for r in result), 2),
        'cost_cny':     round(sum(r['cost_cny'] for r in result), 2),
        'tasks_done':   sum(r['tasks_done'] for r in result),
        'tasks_blocked': sum(r['tasks_blocked'] for r in result),
        'tasks_total':  sum(r['tasks_total'] for r in result),
        'timeout_count': sum(r['timeout_count'] for r in result),
        'scheduler_retries': sum(r['scheduler_retries'] for r in result),
        'task_tokens': sum(r['task_tokens'] for r in result),
        'task_elapsed_sec': sum(r['task_elapsed_sec'] for r in result),
        'task_cost_usd': round(sum(r['task_cost_usd'] for r in result), 4),
        'task_cost_cny': round(sum(r['task_cost_cny'] for r in result), 2),
    }
    terminal_total = totals['tasks_done'] + totals['tasks_blocked']
    totals['success_rate'] = round(totals['tasks_done'] / terminal_total, 4) if terminal_total else 0.0
    totals['timeout_rate'] = round(totals['timeout_count'] / totals['tasks_total'], 4) if totals['tasks_total'] else 0.0
    top = max(result, key=lambda x: x['merit_score'], default={})

    payload = {
        'generatedAt': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'officials': result,
        'totals': totals,
        'top_official': top.get('label',''),
        'top': top,
    }
    atomic_json_write(DATA/'officials_stats.json', payload)
    log.info(f'{len(result)} officials | cost=¥{totals["cost_cny"]} | top={top.get("label","")}')

if __name__ == '__main__':
    main()
