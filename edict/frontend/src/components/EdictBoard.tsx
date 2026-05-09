import { useEffect, useMemo, useState } from 'react';
import { useStore, isEdict, isArchived, isSession, getPipeStatus, stateLabel, deptColor, PIPE, STATE_LABEL, timeAgo } from '../store';
import { api, type Task } from '../api';
import { formatDashboardTime } from '../time';

// ── 排序权重 ──
const STATE_ORDER: Record<string, number> = {
  Doing: 0, Review: 1, Assigned: 2, Menxia: 3, Zhongshu: 4, PendingConfirm: 4,
  Taizi: 5, Inbox: 6, Blocked: 7, Next: 8, Done: 9, Cancelled: 10,
};

// ── Agent maps (from SessionsPanel) ──
function useAgentMaps() {
  const cfg = useStore((s) => s.agentConfig);
  const emojiMap: Record<string, string> = {};
  const labelMap: Record<string, string> = {};
  if (cfg?.agents) {
    cfg.agents.forEach((a) => {
      emojiMap[a.id] = a.emoji || '🏛️';
      labelMap[a.id] = a.label || a.id;
    });
  }
  return { emojiMap, labelMap };
}

function extractAgent(t: Task): string {
  const m = (t.id || '').match(/^OC-(\w+)-/);
  if (m) return m[1];
  return (t.org || '').replace(/省|部/g, '').toLowerCase();
}

function humanTitle(t: Task, labelMap: Record<string, string>): string {
  let title = t.title || '';
  if (title === 'heartbeat 会话') return '💓 心跳检测';
  const m = title.match(/^agent:(\w+):(\w+)/);
  if (m) {
    const agLabel = labelMap[m[1]] || m[1];
    if (m[2] === 'main') return agLabel + ' · 主会话';
    if (m[2] === 'subagent') return agLabel + ' · 子任务执行';
    if (m[2] === 'cron') return agLabel + ' · 定时任务';
    return agLabel + ' · ' + m[2];
  }
  return title.replace(/ 会话$/, '') || t.id;
}

function channelLabel(t: Task): { icon: string; text: string } {
  const now = t.now || '';
  if (now.includes('feishu/direct')) return { icon: '💬', text: '飞书对话' };
  if (now.includes('feishu')) return { icon: '💬', text: '飞书' };
  if (now.includes('webchat')) return { icon: '🌐', text: 'WebChat' };
  if (now.includes('cron')) return { icon: '⏰', text: '定时' };
  if (now.includes('direct')) return { icon: '📨', text: '直连' };
  return { icon: '🔗', text: '会话' };
}

function lastMessage(t: Task): string {
  const acts = t.activity || [];
  for (let i = acts.length - 1; i >= 0; i--) {
    const a = acts[i];
    if (a.kind === 'assistant') {
      let txt = a.text || '';
      if (txt.startsWith('NO_REPLY') || txt.startsWith('Reasoning:')) continue;
      txt = txt.replace(/\[\[.*?\]\]/g, '').replace(/\*\*/g, '').replace(/^#+\s/gm, '').trim();
      return txt.substring(0, 120) + (txt.length > 120 ? '…' : '');
    }
  }
  return '';
}

// ── Mini pipeline (for edict cards) ──

function MiniPipe({ task }: { task: Task }) {
  const stages = getPipeStatus(task);
  return (
    <div className="ec-pipe">
      {stages.map((s, i) => (
        <span key={s.key} style={{ display: 'contents' }}>
          <div className={`ep-node ${s.status}`}>
            <div className="ep-icon">{s.icon}</div>
            <div className="ep-name">{s.dept}</div>
          </div>
          {i < stages.length - 1 && <div className="ep-arrow">›</div>}
        </span>
      ))}
    </div>
  );
}

// ── PendingConfirm Banner ──

type PendingItem = {
  taskId: string;
  title?: string;
  state?: string;
  currentDept?: string;
  requestedAt?: string;
  requestedBy?: string;
  summary?: string;
  comment?: string;
  pending?: boolean;
  approvalState?: string;
};

function PendingConfirmBanner() {
  const toast = useStore((s) => s.toast);
  const loadAll = useStore((s) => s.loadAll);
  const [pendingItems, setPendingItems] = useState<PendingItem[]>([]);
  const [expanded, setExpanded] = useState(false);
  const [loading, setLoading] = useState(false);

  const loadApproval = async () => {
    try {
      const res = await fetch('/api/approval-panel', { cache: 'no-store', credentials: 'same-origin' });
      if (!res.ok) return;
      const json = await res.json();
      setPendingItems(Array.isArray(json.pending) ? json.pending : []);
    } catch {
      // silently fail
    }
  };

  useEffect(() => {
    loadApproval();
    const interval = setInterval(loadApproval, 15000);
    return () => clearInterval(interval);
  }, []);

  const review = async (taskId: string, action: 'approve' | 'reject') => {
    const label = action === 'approve' ? '准奏' : '封驳';
    const comment = prompt(`${label} ${taskId}\n\n请输入批注（可留空）：`);
    if (comment === null) return;
    setLoading(true);
    try {
      const res = await api.reviewAction(taskId, action, comment || '');
      if (!res.ok) throw new Error(res.error || `${label}失败`);
      toast(`✅ ${taskId} 已${label}`, 'ok');
      await Promise.all([loadApproval(), loadAll()]);
    } catch (err) {
      const msg = err instanceof Error ? err.message : `${label}失败`;
      toast(msg, 'err');
    } finally {
      setLoading(false);
    }
  };

  if (pendingItems.length === 0) return null;

  return (
    <div className="pending-banner-wrap">
      <div
        className="pending-banner"
        onClick={() => setExpanded(!expanded)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setExpanded(!expanded); } }}
      >
        <span className="pending-banner-icon">🛡️</span>
        <span className="pending-banner-text">
          <strong>{pendingItems.length} 项待批</strong> — 有待审旨意需要皇上批示
        </span>
        <span className="pending-banner-toggle">{expanded ? '▲ 收起' : '▼ 展开审批'}</span>
      </div>

      {expanded && (
        <div className="pending-banner-body">
          {pendingItems.map((item, idx) => (
            <div className="pending-item" key={`${item.taskId}-${idx}`}>
              <div className="pending-item-info">
                <span className="pending-item-id">{item.taskId}</span>
                <span className="pending-item-title">{item.title || '未命名事项'}</span>
                <span className="pending-item-by">{item.requestedBy || item.currentDept || ''}</span>
              </div>
              <div className="pending-item-actions">
                <button
                  className="btn-refresh"
                  onClick={() => review(item.taskId, 'approve')}
                  disabled={loading}
                >
                  ✅ 准奏
                </button>
                <button
                  className="btn-refresh"
                  onClick={() => review(item.taskId, 'reject')}
                  disabled={loading}
                  style={{ color: 'var(--danger)' }}
                >
                  🚫 封驳
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Edict Card (enhanced: shows both edicts and sessions) ──

function EdictCard({ task }: { task: Task }) {
  const setModalTaskId = useStore((s) => s.setModalTaskId);
  const toast = useStore((s) => s.toast);
  const loadAll = useStore((s) => s.loadAll);
  const { emojiMap, labelMap } = useAgentMaps();

  const edict = isEdict(task);
  const session = isSession(task);
  const hb = task.heartbeat || { status: 'unknown', label: '⚪' };
  const stCls = 'st-' + (task.state || '');
  const deptCls = 'dt-' + (task.org || '').replace(/\s/g, '');
  const todos = task.todos || [];
  const todoDone = todos.filter((x) => x.status === 'completed').length;
  const todoTotal = todos.length;
  const canStop = !['Done', 'Blocked', 'Cancelled'].includes(task.state);
  const canResume = ['Blocked', 'Cancelled'].includes(task.state);
  const archived = isArchived(task);
  const isBlocked = task.block && task.block !== '无' && task.block !== '-';

  // Session-specific fields
  const agent = session ? extractAgent(task) : '';
  const emoji = session ? (emojiMap[agent] || '🏛️') : '';
  const agLabel = session ? (labelMap[agent] || task.org || agent) : '';
  const ch = session ? channelLabel(task) : null;
  const title = session ? humanTitle(task, labelMap) : (task.title || '(无标题)');
  const msg = session ? lastMessage(task) : '';
  const sm = task.sourceMeta || {};
  const totalTk = (sm as Record<string, unknown>).totalTokens as number | undefined;
  const hbDot = hb.status === 'active' ? '🟢' : hb.status === 'warn' ? '🟡' : hb.status === 'stalled' ? '🔴' : '⚪';

  const handleAction = async (action: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (action === 'stop' || action === 'cancel') {
      const reason = prompt(action === 'stop' ? '请输入叫停原因：' : '请输入取消原因：');
      if (reason === null) return;
      try {
        const r = await api.taskAction(task.id, action, reason);
        if (r.ok) { toast(r.message || '操作成功'); loadAll(); }
        else toast(r.error || '操作失败', 'err');
      } catch { toast('服务器连接失败', 'err'); }
    } else if (action === 'resume') {
      try {
        const r = await api.taskAction(task.id, 'resume', '恢复执行');
        if (r.ok) { toast(r.message || '已恢复'); loadAll(); }
        else toast(r.error || '操作失败', 'err');
      } catch { toast('服务器连接失败', 'err'); }
    }
  };

  const handleArchive = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const r = await api.archiveTask(task.id, !task.archived);
      if (r.ok) { toast(r.message || '操作成功'); loadAll(); }
      else toast(r.error || '操作失败', 'err');
    } catch { toast('服务器连接失败', 'err'); }
  };

  // Session card layout (for non-edict tasks)
  if (session && !edict) {
    return (
      <div
        className={`edict-card sess-card-compact${archived ? ' archived' : ''}`}
        onClick={() => setModalTaskId(task.id)}
        style={{ borderLeft: '3px solid var(--line)' }}
      >
        <div className="sc-top">
          <span className="sc-emoji">{emoji}</span>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span className="sc-agent">{agLabel}</span>
              {ch && (
                <span style={{ fontSize: 10, color: 'var(--muted)', background: 'var(--panel2)', padding: '2px 6px', borderRadius: 4 }}>
                  {ch.icon} {ch.text}
                </span>
              )}
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span title={hb.label || ''}>{hbDot}</span>
            <span className={`tag st-${task.state || ''}`} style={{ fontSize: 10 }}>{STATE_LABEL[task.state] || task.state}</span>
          </div>
        </div>
        <div className="ec-id">{task.id}</div>
        <div className="sc-title">{title}</div>
        {msg && (
          <div style={{ fontSize: 11, color: 'var(--muted)', lineHeight: 1.5, marginBottom: 8, borderLeft: '2px solid var(--line)', paddingLeft: 8, maxHeight: 40, overflow: 'hidden' }}>
            {msg}
          </div>
        )}
        <div className="sc-meta">
          {totalTk ? <span style={{ fontSize: 10, color: 'var(--muted)' }}>🪙 {totalTk.toLocaleString()} tokens</span> : null}
          {task.eta ? <span className="sc-time">{timeAgo(task.eta)}</span> : null}
        </div>
        <div className="ec-actions" onClick={(e) => e.stopPropagation()}>
          {canStop && (
            <>
              <button className="mini-act" onClick={(e) => handleAction('stop', e)}>⏸ 叫停</button>
              <button className="mini-act danger" onClick={(e) => handleAction('cancel', e)}>🚫 取消</button>
            </>
          )}
          {canResume && (
            <button className="mini-act" onClick={(e) => handleAction('resume', e)}>▶ 恢复</button>
          )}
          {task.archived && (
            <button className="mini-act" onClick={handleArchive}>📤 取消归档</button>
          )}
          {!task.archived && (
            <button className="mini-act" onClick={handleArchive}>📦 归档</button>
          )}
        </div>
      </div>
    );
  }

  // Edict card layout (for JJC-* tasks)
  const curStage = PIPE.find((_, i) => getPipeStatus(task)[i].status === 'active');

  return (
    <div
      className={`edict-card${archived ? ' archived' : ''}${edict ? ' edict-highlight' : ''}`}
      onClick={() => setModalTaskId(task.id)}
    >
      <MiniPipe task={task} />
      <div className="ec-id">{task.id}</div>
      <div className="ec-title">{title}</div>
      <div className="ec-meta">
        <span className={`tag ${stCls}`}>{stateLabel(task)}</span>
        {task.org && <span className={`tag ${deptCls}`}>{task.org}</span>}
        {curStage && (
          <span style={{ fontSize: 11, color: 'var(--muted)' }}>
            当前: <b style={{ color: deptColor(curStage.dept) }}>{curStage.dept} · {curStage.action}</b>
          </span>
        )}
      </div>
      {task.now && task.now !== '-' && (
        <div style={{ fontSize: 11, color: 'var(--muted)', lineHeight: 1.5, marginBottom: 6 }}>
          {task.now.substring(0, 80)}
        </div>
      )}
      {(task.review_round || 0) > 0 && (
        <div style={{ fontSize: 11, marginBottom: 6 }}>
          {Array.from({ length: task.review_round || 0 }, (_, i) => (
            <span
              key={i}
              style={{
                display: 'inline-block', width: 14, height: 14, borderRadius: '50%',
                background: i < (task.review_round || 0) - 1 ? '#1a3a6a22' : 'var(--acc)22',
                border: `1px solid ${i < (task.review_round || 0) - 1 ? '#2a4a8a' : 'var(--acc)'}`,
                fontSize: 9, textAlign: 'center', lineHeight: '13px', marginRight: 2,
                color: i < (task.review_round || 0) - 1 ? '#4a6aaa' : 'var(--acc)',
              }}
            >
              {i + 1}
            </span>
          ))}
          <span style={{ color: 'var(--muted)', fontSize: 10 }}>第 {task.review_round} 轮磋商</span>
        </div>
      )}
      {todoTotal > 0 && (
        <div className="ec-todo-bar">
          <span>📋 {todoDone}/{todoTotal}</span>
          <div className="ec-todo-track">
            <div className="ec-todo-fill" style={{ width: `${Math.round((todoDone / todoTotal) * 100)}%` }} />
          </div>
          <span>{todoDone === todoTotal ? '✅ 全部完成' : '🔄 进行中'}</span>
        </div>
      )}
      <div className="ec-footer">
        <span className={`hb ${hb.status}`}>{hb.label}</span>
        {isBlocked && (
          <span className="tag" style={{ borderColor: '#ff527044', color: 'var(--danger)', background: '#200a10' }}>
            🚫 {task.block}
          </span>
        )}
        {task.eta && task.eta !== '-' && (
          <span style={{ fontSize: 11, color: 'var(--muted)' }}>📅 {task.eta}</span>
        )}
      </div>
      <div className="ec-actions" onClick={(e) => e.stopPropagation()}>
        {canStop && (
          <>
            <button className="mini-act" onClick={(e) => handleAction('stop', e)}>⏸ 叫停</button>
            <button className="mini-act danger" onClick={(e) => handleAction('cancel', e)}>🚫 取消</button>
          </>
        )}
        {canResume && (
          <button className="mini-act" onClick={(e) => handleAction('resume', e)}>▶ 恢复</button>
        )}
        {archived && !task.archived && (
          <button className="mini-act" onClick={handleArchive}>📦 归档</button>
        )}
        {task.archived && (
          <button className="mini-act" onClick={handleArchive}>📤 取消归档</button>
        )}
      </div>
    </div>
  );
}

// ── Main Board ──

export default function EdictBoard() {
  const liveStatus = useStore((s) => s.liveStatus);
  const edictFilter = useStore((s) => s.edictFilter);
  const setEdictFilter = useStore((s) => s.setEdictFilter);
  const edictSourceFilter = useStore((s) => s.edictSourceFilter);
  const setEdictSourceFilter = useStore((s) => s.setEdictSourceFilter);
  const edictAgentFilter = useStore((s) => s.edictAgentFilter);
  const setEdictAgentFilter = useStore((s) => s.setEdictAgentFilter);
  const agentConfig = useStore((s) => s.agentConfig);
  const toast = useStore((s) => s.toast);
  const loadAll = useStore((s) => s.loadAll);

  const tasks = liveStatus?.tasks || [];

  // Build agent list for filter
  const agentMap: Record<string, string> = {};
  if (agentConfig?.agents) {
    agentConfig.agents.forEach((a) => { agentMap[a.id] = a.label || a.id; });
  }

  // Separate edicts and sessions for counts
  const allEdicts = tasks.filter(isEdict);
  const allSessions = tasks.filter((t) => !isEdict(t));
  const activeEdicts = allEdicts.filter((t) => !isArchived(t));
  const archivedEdicts = allEdicts.filter((t) => isArchived(t));

  // Step 1: Apply source filter
  let sourceFiltered: Task[];
  if (edictSourceFilter === 'jjc') {
    sourceFiltered = tasks.filter(isEdict);
  } else {
    sourceFiltered = [...tasks]; // all tasks
  }

  // Step 2: Apply agent filter (for non-edict tasks)
  if (edictAgentFilter !== 'all') {
    sourceFiltered = sourceFiltered.filter((t) => {
      if (isEdict(t)) return true; // always show edicts
      return extractAgent(t) === edictAgentFilter;
    });
  }

  // Step 3: Apply active/archived filter
  let filtered: Task[];
  if (edictFilter === 'active') filtered = sourceFiltered.filter((t) => !isArchived(t));
  else if (edictFilter === 'archived') filtered = sourceFiltered.filter((t) => isArchived(t));
  else filtered = sourceFiltered;

  // Sort: edicts first (by state), then sessions (by state)
  filtered.sort((a, b) => {
    const aEdict = isEdict(a) ? 0 : 1;
    const bEdict = isEdict(b) ? 0 : 1;
    if (aEdict !== bEdict) return aEdict - bEdict;
    return (STATE_ORDER[a.state] ?? 9) - (STATE_ORDER[b.state] ?? 9);
  });

  const unArchivedDone = allEdicts.filter((t) => !t.archived && ['Done', 'Cancelled'].includes(t.state));

  // Unique agents for filter
  const sessionAgentIds = [...new Set(allSessions.map(extractAgent))];

  const handleArchiveAll = async () => {
    if (!confirm('将所有已完成/已取消的旨意移入归档？')) return;
    try {
      const r = await api.archiveAllDone();
      if (r.ok) { toast(`📦 ${r.count || 0} 道旨意已归档`); loadAll(); }
      else toast(r.error || '批量归档失败', 'err');
    } catch { toast('服务器连接失败', 'err'); }
  };

  const handleScan = async () => {
    try {
      const r = await api.schedulerScan();
      if (r.ok) toast(`🧭 太子巡检完成：${r.count || 0} 个动作`);
      else toast(r.error || '巡检失败', 'err');
      loadAll();
    } catch { toast('服务器连接失败', 'err'); }
  };

  return (
    <div>
      {/* PendingConfirm Banner - embedded at top */}
      <PendingConfirmBanner />

      {/* Filter Bar */}
      <div className="archive-bar">
        <span className="ab-label">状态:</span>
        {(['active', 'archived', 'all'] as const).map((f) => (
          <button
            key={f}
            className={`ab-btn ${edictFilter === f ? 'active' : ''}`}
            onClick={() => setEdictFilter(f)}
          >
            {f === 'active' ? '活跃' : f === 'archived' ? '归档' : '全部'}
          </button>
        ))}

        <span className="ab-label" style={{ marginLeft: 12 }}>来源:</span>
        <button
          className={`ab-btn ${edictSourceFilter === 'all' ? 'active' : ''}`}
          onClick={() => setEdictSourceFilter('all')}
        >
          全部任务 ({tasks.length})
        </button>
        <button
          className={`ab-btn ${edictSourceFilter === 'jjc' ? 'active' : ''}`}
          onClick={() => setEdictSourceFilter('jjc')}
        >
          📜 JJC 旨意 ({allEdicts.length})
        </button>

        {sessionAgentIds.length > 0 && (
          <>
            <span className="ab-label" style={{ marginLeft: 12 }}>Agent:</span>
            <button
              className={`ab-btn ${edictAgentFilter === 'all' ? 'active' : ''}`}
              onClick={() => setEdictAgentFilter('all')}
            >
              全部
            </button>
            {sessionAgentIds.slice(0, 6).map((id) => (
              <button
                key={id}
                className={`ab-btn ${edictAgentFilter === id ? 'active' : ''}`}
                onClick={() => setEdictAgentFilter(id)}
              >
                {agentMap[id] || id}
              </button>
            ))}
          </>
        )}

        {unArchivedDone.length > 0 && (
          <button className="ab-btn" onClick={handleArchiveAll}>📦 一键归档</button>
        )}
        <span className="ab-count">
          活跃 {tasks.filter((t) => !isArchived(t) && !['Done', 'Cancelled'].includes(t.state)).length} ·
          旨意 {activeEdicts.length} ·
          会话 {allSessions.filter((t) => !isArchived(t)).length} ·
          归档 {tasks.filter(isArchived).length}
        </span>
        <button className="ab-scan" onClick={handleScan}>🧭 太子巡检</button>
      </div>

      {/* Grid */}
      <div className="edict-grid">
        {filtered.length === 0 ? (
          <div className="empty" style={{ gridColumn: '1/-1' }}>
            暂无数据<br />
            <small style={{ fontSize: 11, marginTop: 6, display: 'block', color: 'var(--muted)' }}>
              {edictSourceFilter === 'jjc'
                ? '通过飞书向太子发送任务，太子分拣后转中书省处理'
                : '切换筛选条件查看更多内容'}
            </small>
          </div>
        ) : (
          filtered.map((t) => <EdictCard key={t.id} task={t} />)
        )}
      </div>
    </div>
  );
}
