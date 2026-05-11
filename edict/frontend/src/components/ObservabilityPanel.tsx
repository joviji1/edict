import { useEffect, useMemo, useState } from 'react';
import { api, type ObservabilityPanelData, type ObservabilityItem } from '../api';
import { useStore, timeAgo } from '../store';
import { formatDashboardDateTime } from '../time';

function when(value?: string | number) {
  if (!value) return '时间待补';
  if (typeof value === 'number') return String(value);
  return `${formatDashboardDateTime(value, { showSeconds: true })} · ${timeAgo(value)}`;
}

function itemKey(item: ObservabilityItem, idx: number) {
  return `${item.taskId || item.sessionId || item.agentId || item.source || 'obs'}-${item.at || item.updatedAt || idx}-${idx}`;
}

function Metric({ label, value, tone }: { label: string; value: string | number; tone?: string }) {
  return (
    <div className="kpi">
      <div className={`kpi-v ${tone || ''}`}>{value}</div>
      <div className="kpi-l">{label}</div>
    </div>
  );
}

function ObsList({ items, empty, render }: { items: ObservabilityItem[]; empty: string; render: (item: ObservabilityItem, idx: number) => JSX.Element }) {
  if (!items.length) return <div className="empty">{empty}</div>;
  return <div className="obs-list">{items.map(render)}</div>;
}

export default function ObservabilityPanel() {
  const toast = useStore((s) => s.toast);
  const setModalTaskId = useStore((s) => s.setModalTaskId);
  const [data, setData] = useState<ObservabilityPanelData | null>(null);
  const [query, setQuery] = useState('');
  const [draft, setDraft] = useState('');
  const [loading, setLoading] = useState(false);

  const load = async (nextQuery = query) => {
    setLoading(true);
    try {
      const payload = await api.observabilityPanel(nextQuery, 20);
      setData(payload);
    } catch (err) {
      toast(err instanceof Error ? err.message : '观星台加载失败', 'err');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load('');
  }, []);

  const searchItems = useMemo(() => data?.search?.items || [], [data]);
  const logItems = useMemo(() => data?.logs?.items || [], [data]);
  const cronItems = useMemo(() => data?.cron?.items || [], [data]);
  const sessionItems = useMemo(() => data?.sessions?.items || [], [data]);
  const tokenItems = useMemo(() => data?.tokens?.items || [], [data]);

  const doSearch = () => {
    const next = draft.trim();
    setQuery(next);
    load(next);
  };

  return (
    <div className="observability-wrap">
      <section className="governance-panel obs-hero">
        <div className="governance-head">
          <div>
            <div className="governance-title">🔭 观星台</div>
            <div className="governance-sub">搜索 / 日志 / Cron / Session / Token 只读观测面</div>
          </div>
          <div className="governance-actions archive-search-bar">
            <input
              className="archive-search-input"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') doSearch(); }}
              placeholder="搜索任务号 / key / token / 兼容路径"
            />
            <button className="btn-refresh" onClick={doSearch} disabled={loading}>{loading ? '检索中…' : '检索'}</button>
            <button className="btn-refresh" onClick={() => load(query)} disabled={loading}>刷新</button>
          </div>
        </div>
        <div className="governance-kpis obs-kpis">
          <Metric label="匹配任务" value={data?.stats?.matchingTasks ?? 0} tone="blue" />
          <Metric label="活跃任务" value={data?.stats?.activeTasks ?? 0} tone="green" />
          <Metric label="调度项" value={data?.stats?.cronItems ?? 0} tone="warn" />
          <Metric label="Token" value={data?.tokens?.summary?.totalTokens ?? 0} tone="gold" />
        </div>
        <div className="obs-meta-row">
          <span className="chip">query: {data?.query || '全部'}</span>
          <span className="chip">cost: ${(data?.tokens?.summary?.totalCostUsd ?? 0).toFixed(4)}</span>
          <span className="chip">gateway token: {data?.tokens?.gatewayAuth?.configured ? data.tokens.gatewayAuth.redactedToken : '未配置'}</span>
          <span className="chip">checked: {data?.checkedAt ? when(data.checkedAt) : '待加载'}</span>
        </div>
        <div className="obs-meta-row">
          <span className="chip">tasks_source: {data?.sources?.tasksSource?.count ?? '-'}</span>
          <span className="chip">live_status: {data?.sources?.liveStatus?.count ?? '-'}</span>
          <span className="chip">backend DB: {data?.sources?.backendDb?.count ?? '-'}</span>
          <span className="chip">三面一致: {data?.sources ? (data.sources.consistent ? '是' : '否') : '待加载'}</span>
        </div>
      </section>

      <div className="obs-grid">
        <section className="governance-panel obs-card">
          <div className="governance-title small">🔎 搜索</div>
          <ObsList items={searchItems} empty="暂无匹配任务" render={(item, idx) => (
            <article className="obs-item clickable" key={itemKey(item, idx)} onClick={() => item.taskId && setModalTaskId(item.taskId)}>
              <div className="obs-top"><b>{item.taskId}</b><span className={`tag st-${item.state}`}>{item.state}</span></div>
              <div className="obs-title">{item.title}</div>
              <div className="obs-text">{item.matchedText}</div>
              <div className="obs-foot">{item.org} · {when(item.updatedAt)}</div>
            </article>
          )} />
        </section>

        <section className="governance-panel obs-card">
          <div className="governance-title small">📜 日志</div>
          <ObsList items={logItems} empty="暂无日志条目" render={(item, idx) => (
            <article className={`obs-item level-${item.level || 'info'}`} key={itemKey(item, idx)}>
              <div className="obs-top"><b>{item.source}</b><span>{item.taskId}</span></div>
              <div className="obs-text">{item.summary}</div>
              <div className="obs-foot">{when(item.at)}</div>
            </article>
          )} />
        </section>

        <section className="governance-panel obs-card">
          <div className="governance-title small">⏱️ Cron / Scheduler</div>
          <ObsList items={cronItems} empty="暂无调度项" render={(item, idx) => (
            <article className="obs-item" key={itemKey(item, idx)}>
              <div className="obs-top"><b>{item.taskId}</b><span className="chip">retry {item.retryCount || 0}</span></div>
              <div className="obs-title">{item.title}</div>
              <div className="obs-text">{item.lastDispatchStatus}{item.lastDispatchError ? ` · ${item.lastDispatchError}` : ''}</div>
              <div className="obs-foot">{when(item.lastDispatchAt)}</div>
            </article>
          )} />
        </section>

        <section className="governance-panel obs-card">
          <div className="governance-title small">🧵 Session</div>
          <ObsList items={sessionItems} empty="暂无匹配会话" render={(item, idx) => (
            <article className="obs-item" key={itemKey(item, idx)}>
              <div className="obs-top"><b>{item.agentId}</b><span>{item.sessionKey || item.sessionId}</span></div>
              <div className="obs-title">{item.title}</div>
              <div className="obs-text">{item.excerpt}</div>
              <div className="obs-foot">{when(item.updatedAt)}</div>
            </article>
          )} />
        </section>

        <section className="governance-panel obs-card obs-wide">
          <div className="governance-title small">🪙 Token / Cost</div>
          <ObsList items={tokenItems} empty="暂无 token 使用记录" render={(item, idx) => (
            <article className="obs-item" key={itemKey(item, idx)}>
              <div className="obs-top"><b>{item.taskId}</b><span>{item.tokens || 0} tokens</span><span>${Number(item.costUsd || 0).toFixed(4)}</span></div>
              <div className="obs-title">{item.title}</div>
              <div className="obs-text">{item.summary}</div>
              <div className="obs-foot">{when(item.at)}</div>
            </article>
          )} />
        </section>
      </div>
    </div>
  );
}
