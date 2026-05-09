import { useEffect, useMemo, useState } from 'react';
import { api, type GuoshiguanPanelItem, type JidipuPanelItem } from '../api';
import { useStore, timeAgo } from '../store';
import { formatDashboardDateTime } from '../time';

const JIDIPU_KIND_META: Record<string, { icon: string; cls: string; label: string }> = {
  dispatch: { icon: '📮', cls: 'dispatch', label: '派发' },
  notification: { icon: '🔔', cls: 'notification', label: '通知' },
  retry: { icon: '🔁', cls: 'retry', label: '重试' },
  escalation: { icon: '🚨', cls: 'escalation', label: '升级' },
  approval: { icon: '🛡️', cls: 'approval', label: '审批' },
};

function kindMeta(item: JidipuPanelItem) {
  return JIDIPU_KIND_META[item.kind] || { icon: '📌', cls: 'generic', label: item.kindLabel || item.kind || '动态' };
}

function sourceLabel(sourceType: string) {
  if (sourceType === 'task_memory') return '任务记忆';
  if (sourceType === 'autopsy') return '复盘档案';
  if (sourceType === 'shared_rule') return '共享规约';
  return sourceType || '资料';
}

function renderUpdatedAt(value?: string) {
  if (!value) return '待补时间';
  return `${formatDashboardDateTime(value, { showSeconds: true })} · ${timeAgo(value)}`;
}

function CitationTrail({ item }: { item: GuoshiguanPanelItem }) {
  const trail = [
    item.taskId ? `任务 ${item.taskId}` : '',
    item.sourceType ? sourceLabel(item.sourceType) : '',
    item.agentId ? `归档官员 ${item.agentId}` : '',
    item.path ? '原文摘录' : '',
  ].filter(Boolean);

  if (!trail.length) return null;

  return (
    <div className="archive-citation-chain">
      {trail.map((part, idx) => (
        <span key={`${part}-${idx}`} className="archive-citation-node">
          {part}
        </span>
      ))}
    </div>
  );
}

export default function RelayArchivePanel() {
  const toast = useStore((s) => s.toast);
  const setModalTaskId = useStore((s) => s.setModalTaskId);
  const [jidipu, setJidipu] = useState<any>(null);
  const [guoshi, setGuoshi] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [query, setQuery] = useState('');
  const [draftQuery, setDraftQuery] = useState('');
  const [jidipuTaskFilter, setJidipuTaskFilter] = useState('');

  const load = async (nextQuery = query) => {
    setLoading(true);
    try {
      const [jidipuData, guoshiData] = await Promise.all([
        api.jidipuPanel(18, jidipuTaskFilter || undefined),
        api.guoshiguanPanel(nextQuery, 18),
      ]);
      setJidipu(jidipuData);
      setGuoshi(guoshiData);
    } catch (err) {
      const msg = err instanceof Error ? err.message : '急递铺 / 国史馆加载失败';
      toast(msg, 'err');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [jidipuTaskFilter]);

  const jidipuItems = useMemo(() => (Array.isArray(jidipu?.items) ? jidipu.items : []), [jidipu]);
  const guoshiItems = useMemo(() => (Array.isArray(guoshi?.items) ? guoshi.items : []), [guoshi]);
  const highlights = useMemo(() => (Array.isArray(guoshi?.highlights) ? guoshi.highlights : []), [guoshi]);

  // Extract unique task IDs from jidipu for filter dropdown
  const jidipuTaskIds = useMemo(() => {
    const ids = new Set<string>();
    (Array.isArray(jidipu?.items) ? jidipu.items : []).forEach((item: JidipuPanelItem) => {
      if (item.taskId) ids.add(item.taskId);
    });
    return [...ids].sort();
  }, [jidipu]);

  const handleSearch = () => {
    const next = draftQuery.trim();
    setQuery(next);
    load(next);
  };

  return (
    <div className="relay-archive-wrap">
      <div className="relay-archive-grid">
        <section className="governance-panel relay-panel">
          <div className="governance-head">
            <div>
              <div className="governance-title">🚀 急递铺</div>
              <div className="governance-sub">派发 / 通知 / 审批 / 重试升级消息流</div>
            </div>
            <div className="governance-actions">
              <span className="chip">总条目 {jidipu?.stats?.total || 0}</span>
              {jidipuTaskIds.length > 1 && (
                <select
                  className="archive-search-input"
                  style={{ maxWidth: 160, padding: '4px 8px', fontSize: 11 }}
                  value={jidipuTaskFilter}
                  onChange={(e) => setJidipuTaskFilter(e.target.value)}
                >
                  <option value="">全部任务</option>
                  {jidipuTaskIds.map((tid) => (
                    <option key={tid} value={tid}>{tid}</option>
                  ))}
                </select>
              )}
              <button className="btn-refresh" onClick={() => load()} disabled={loading}>
                {loading ? '刷新中…' : '刷新'}
              </button>
            </div>
          </div>

          <div className="governance-kpis relay-kpis">
            <div className="kpi"><div className="kpi-v" style={{ color: 'var(--acc)' }}>{jidipu?.stats?.dispatches || 0}</div><div className="kpi-l">派发</div></div>
            <div className="kpi"><div className="kpi-v" style={{ color: '#7dd3fc' }}>{jidipu?.stats?.notifications || 0}</div><div className="kpi-l">通知</div></div>
            <div className="kpi"><div className="kpi-v" style={{ color: '#f5c842' }}>{jidipu?.stats?.retries || 0}</div><div className="kpi-l">重试</div></div>
            <div className="kpi"><div className="kpi-v" style={{ color: 'var(--danger)' }}>{jidipu?.stats?.escalations || 0}</div><div className="kpi-l">升级</div></div>
          </div>

          {!jidipuItems.length ? (
            <div className="empty">暂无急递铺流转数据</div>
          ) : (
            <div className="relay-timeline">
              {jidipuItems.map((item: JidipuPanelItem, idx: number) => {
                const meta = kindMeta(item);
                const canOpenTask = !!item.taskId;
                return (
                  <article
                    key={`${item.taskId}-${item.at || idx}-${meta.cls}`}
                    className={`relay-entry ${meta.cls}${canOpenTask ? ' clickable' : ''}`}
                    onClick={canOpenTask ? () => setModalTaskId(item.taskId) : undefined}
                    role={canOpenTask ? 'button' : undefined}
                    tabIndex={canOpenTask ? 0 : undefined}
                    onKeyDown={canOpenTask ? (e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        setModalTaskId(item.taskId);
                      }
                    } : undefined}
                  >
                    <div className="relay-line" />
                    <div className={`relay-dot ${meta.cls}`}>{meta.icon}</div>
                    <div className="relay-card">
                      <div className="relay-card-top">
                        <div>
                          <div className="relay-task-id">{item.taskId}</div>
                          <div className="relay-card-title">{item.title || '未命名事项'}</div>
                        </div>
                        <span className={`relay-kind ${meta.cls}`}>{item.kindLabel || meta.label}</span>
                      </div>
                      <div className="relay-route">
                        <span>{item.from || '来源待补'}</span>
                        <span className="relay-arrow">→</span>
                        <span>{item.to || '去向待补'}</span>
                        <span className={`tag st-${item.state}`}>{item.state || 'Unknown'}</span>
                      </div>
                      {item.summary ? <div className="relay-summary">{item.summary}</div> : null}
                      <div className="relay-meta">
                        <span>{renderUpdatedAt(item.at)}</span>
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </section>

        <section className="governance-panel archive-panel">
          <div className="governance-head archive-head">
            <div>
              <div className="governance-title">🏛️ 国史馆</div>
              <div className="governance-sub">任务记忆 / 复盘档案 / 共享规约统一检索</div>
            </div>
            <div className="governance-actions archive-search-bar">
              <input
                className="archive-search-input"
                value={draftQuery}
                onChange={(e) => setDraftQuery(e.target.value)}
                placeholder="输入任务号 / 关键词 / 规则名"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleSearch();
                }}
              />
              <button className="btn-refresh" onClick={handleSearch} disabled={loading}>检索</button>
            </div>
          </div>

          <div className="governance-kpis archive-kpis">
            <div className="kpi"><div className="kpi-v" style={{ color: 'var(--acc)' }}>{guoshi?.stats?.shown || 0}</div><div className="kpi-l">当前展示</div></div>
            <div className="kpi"><div className="kpi-v" style={{ color: '#7dd3fc' }}>{guoshi?.stats?.taskMemory || 0}</div><div className="kpi-l">任务记忆</div></div>
            <div className="kpi"><div className="kpi-v" style={{ color: '#f5c842' }}>{guoshi?.stats?.autopsy || 0}</div><div className="kpi-l">复盘档案</div></div>
            <div className="kpi"><div className="kpi-v" style={{ color: '#c084fc' }}>{guoshi?.stats?.sharedRules || 0}</div><div className="kpi-l">共享规约</div></div>
          </div>

          {highlights.length > 0 && (
            <div className="archive-highlight-row">
              {highlights.slice(0, 3).map((item: any, idx: number) => (
                <div className="archive-highlight" key={`${item.taskId}-${idx}`}>
                  <div className="archive-highlight-label">{sourceLabel(item.sourceType)}</div>
                  <div className="archive-highlight-title">{item.title}</div>
                  {item.summary ? <div className="archive-highlight-summary">{item.summary}</div> : null}
                </div>
              ))}
            </div>
          )}

          {!guoshiItems.length ? (
            <div className="empty">暂无国史馆条目</div>
          ) : (
            <div className="archive-list">
              {guoshiItems.map((item: GuoshiguanPanelItem, idx: number) => {
                const canOpenTask = !!item.taskId;
                return (
                  <article
                    className={`archive-item${canOpenTask ? ' clickable' : ''}`}
                    key={`${item.taskId}-${item.path || idx}`}
                    onClick={canOpenTask ? () => setModalTaskId(item.taskId) : undefined}
                    role={canOpenTask ? 'button' : undefined}
                    tabIndex={canOpenTask ? 0 : undefined}
                    onKeyDown={canOpenTask ? (e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        setModalTaskId(item.taskId);
                      }
                    } : undefined}
                  >
                    <div className="archive-item-top">
                      <div>
                        <div className="archive-task-id">{item.taskId}</div>
                        <div className="archive-item-title">{item.title || '未命名档案'}</div>
                      </div>
                      <span className="archive-source-badge">{sourceLabel(item.sourceType)}</span>
                    </div>
                    {item.summary ? <div className="archive-summary">{item.summary}</div> : null}
                    <CitationTrail item={item} />
                    {Array.isArray(item.tags) && item.tags.length > 0 ? (
                      <div className="archive-tag-row">
                        {item.tags.slice(0, 6).map((tag) => (
                          <span className="archive-tag" key={`${item.taskId}-${tag}`}>{tag}</span>
                        ))}
                      </div>
                    ) : null}
                    {Array.isArray(item.keyDecisions) && item.keyDecisions.length > 0 ? (
                      <ul className="archive-decisions">
                        {item.keyDecisions.slice(0, 3).map((decision, didx) => (
                          <li key={`${item.taskId}-decision-${didx}`}>{decision}</li>
                        ))}
                      </ul>
                    ) : null}
                    {item.excerpt ? <div className="archive-excerpt">{item.excerpt}</div> : null}
                    <div className="archive-meta">
                      <span>{renderUpdatedAt(item.updatedAt)}</span>
                      {item.path ? <span className="archive-path">{item.path}</span> : null}
                    </div>
                  </article>
              );
            })}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
