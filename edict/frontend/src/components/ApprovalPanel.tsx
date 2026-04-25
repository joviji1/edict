import { useEffect, useMemo, useState } from 'react';
import { api } from '../api';
import { useStore, timeAgo } from '../store';

type ApprovalItem = {
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

type ApprovalHistoryItem = {
  taskId: string;
  title?: string;
  result?: string;
  action?: string;
  approver?: string;
  at?: string;
  comment?: string;
};

type ApprovalPanelData = {
  pending?: ApprovalItem[];
  history?: ApprovalHistoryItem[];
  stats?: {
    pendingCount?: number;
    approvedCount?: number;
    rejectedCount?: number;
    total?: number;
  };
};

function statusText(value?: string) {
  if (value === 'approved' || value === 'approve') return '已准奏';
  if (value === 'rejected' || value === 'reject') return '已封驳';
  return '待处理';
}

function statusClass(value?: string) {
  if (value === 'approved' || value === 'approve') return 'approved';
  if (value === 'rejected' || value === 'reject') return 'rejected';
  return 'pending';
}

function fmtTime(value?: string) {
  if (!value) return '待补时间';
  return `${value} · ${timeAgo(value)}`;
}

export default function ApprovalPanel() {
  const toast = useStore((s) => s.toast);
  const loadAll = useStore((s) => s.loadAll);
  const [data, setData] = useState<ApprovalPanelData | null>(null);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const result = await fetch('/api/approval-panel', { cache: 'no-store', credentials: 'same-origin' });
      if (!result.ok) {
        const text = await result.text();
        throw new Error(text || `HTTP ${result.status}`);
      }
      const json = (await result.json()) as ApprovalPanelData;
      setData(json);
    } catch (err) {
      const msg = err instanceof Error ? err.message : '待批专面板加载失败';
      toast(msg, 'err');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const pendingItems = useMemo(() => (Array.isArray(data?.pending) ? data!.pending! : []), [data]);
  const historyItems = useMemo(() => (Array.isArray(data?.history) ? data!.history! : []), [data]);

  const review = async (taskId: string, action: 'approve' | 'reject') => {
    const label = action === 'approve' ? '准奏' : '封驳';
    const comment = prompt(`${label} ${taskId}\n\n请输入批注（可留空）：`);
    if (comment === null) return;
    try {
      const res = await api.reviewAction(taskId, action, comment || '');
      if (!res.ok) throw new Error(res.error || `${label}失败`);
      toast(`✅ ${taskId} 已${label}`, 'ok');
      await Promise.all([load(), loadAll()]);
    } catch (err) {
      const msg = err instanceof Error ? err.message : `${label}失败`;
      toast(msg, 'err');
    }
  };

  const stats = data?.stats || {};

  return (
    <div className="relay-archive-wrap">
      <div className="relay-archive-grid">
        <section className="governance-panel relay-panel">
          <div className="governance-head">
            <div>
              <div className="governance-title">🛡️ 待批专面板</div>
              <div className="governance-sub">集中处理 PendingConfirm 事项，可直接准奏 / 封驳并查看审批流转历史</div>
            </div>
            <div className="governance-actions">
              <span className="chip">待批 {stats.pendingCount || pendingItems.length}</span>
              <button className="btn-refresh" onClick={load} disabled={loading}>
                {loading ? '刷新中…' : '刷新'}
              </button>
            </div>
          </div>

          <div className="governance-kpis relay-kpis">
            <div className="kpi"><div className="kpi-v" style={{ color: '#f5c842' }}>{stats.pendingCount || pendingItems.length}</div><div className="kpi-l">待批</div></div>
            <div className="kpi"><div className="kpi-v" style={{ color: '#2ecc8a' }}>{stats.approvedCount || 0}</div><div className="kpi-l">已准奏</div></div>
            <div className="kpi"><div className="kpi-v" style={{ color: '#ff5270' }}>{stats.rejectedCount || 0}</div><div className="kpi-l">已封驳</div></div>
            <div className="kpi"><div className="kpi-v" style={{ color: 'var(--acc)' }}>{stats.total || historyItems.length}</div><div className="kpi-l">历史总数</div></div>
          </div>

          {!pendingItems.length ? (
            <div className="empty">当前没有待批事项</div>
          ) : (
            <div className="relay-timeline">
              {pendingItems.map((item, idx) => (
                <article key={`${item.taskId}-${idx}`} className="relay-entry approval">
                  <div className="relay-line" />
                  <div className="relay-dot approval">🛡️</div>
                  <div className="relay-card">
                    <div className="relay-card-top">
                      <div>
                        <div className="relay-task-id">{item.taskId}</div>
                        <div className="relay-card-title">{item.title || '未命名事项'}</div>
                      </div>
                      <span className={`relay-kind ${statusClass(item.approvalState || item.state)}`}>{statusText(item.approvalState || item.state)}</span>
                    </div>
                    <div className="relay-route">
                      <span>{item.requestedBy || item.currentDept || '待补来源'}</span>
                      <span className="relay-arrow">→</span>
                      <span>皇上批示</span>
                      <span className={`tag st-${item.state || 'PendingConfirm'}`}>{item.state || 'PendingConfirm'}</span>
                    </div>
                    {item.summary ? <div className="relay-summary">{item.summary}</div> : null}
                    {item.comment ? <div className="relay-summary">批注：{item.comment}</div> : null}
                    <div className="relay-meta">
                      <span>{fmtTime(item.requestedAt)}</span>
                    </div>
                    <div className="governance-actions" style={{ marginTop: 10 }}>
                      <button className="btn-refresh" onClick={() => review(item.taskId, 'approve')}>✅ 准奏</button>
                      <button className="btn-refresh" onClick={() => review(item.taskId, 'reject')}>🚫 封驳</button>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>

        <section className="governance-panel archive-panel">
          <div className="governance-head archive-head">
            <div>
              <div className="governance-title">📜 审批历史</div>
              <div className="governance-sub">展示已准奏 / 已封驳记录，便于回溯批示结果与批注</div>
            </div>
          </div>

          {!historyItems.length ? (
            <div className="empty">暂无审批历史</div>
          ) : (
            <div className="archive-list">
              {historyItems.map((item, idx) => (
                <article className="archive-item" key={`${item.taskId}-${item.at || idx}`}>
                  <div className="archive-item-top">
                    <div>
                      <div className="archive-task-id">{item.taskId}</div>
                      <div className="archive-item-title">{item.title || '未命名事项'}</div>
                    </div>
                    <span className={`archive-source-badge ${statusClass(item.result || item.action)}`}>{statusText(item.result || item.action)}</span>
                  </div>
                  {item.comment ? <div className="archive-summary">批注：{item.comment}</div> : null}
                  <div className="archive-meta">
                    <span>{fmtTime(item.at)}</span>
                    {item.approver ? <span className="archive-path">{item.approver}</span> : null}
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
