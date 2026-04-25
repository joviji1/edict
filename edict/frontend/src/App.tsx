import { useEffect, useState, type FormEvent } from 'react';
import { useStore, TAB_DEFS, startPolling, stopPolling, isEdict, isArchived } from './store';
import EdictBoard from './components/EdictBoard';
import MonitorPanel from './components/MonitorPanel';
import ModelConfig from './components/ModelConfig';
import SkillsConfig from './components/SkillsConfig';
import SessionsPanel from './components/SessionsPanel';
import MemorialPanel from './components/MemorialPanel';
import TemplatePanel from './components/TemplatePanel';
import MorningPanel from './components/MorningPanel';
import RelayArchivePanel from './components/RelayArchivePanel';
import ApprovalPanel from './components/ApprovalPanel';
import OfficialPanel from './components/OfficialPanel';
import TaskModal from './components/TaskModal';
import Toaster from './components/Toaster';
import CourtCeremony from './components/CourtCeremony';
import CourtDiscussion from './components/CourtDiscussion';

function AuthGate() {
  const login = useStore((s) => s.login);
  const authError = useStore((s) => s.authError);
  const [password, setPassword] = useState('');
  const [pending, setPending] = useState(false);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!password.trim() || pending) return;
    setPending(true);
    const ok = await login(password);
    if (!ok) setPending(false);
  };

  return (
    <div className="auth-wrap">
      <form className="auth-card" onSubmit={handleSubmit}>
        <div className="auth-title">三省六部 · 登录验证</div>
        <div className="auth-sub">看板已开启密码保护。登录后即可看到最新旨意与流转。</div>
        <input
          className="auth-input"
          type="password"
          placeholder="请输入看板密码"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoFocus
        />
        {authError ? <div className="auth-error">{authError}</div> : null}
        <button className="auth-btn" type="submit" disabled={pending || !password.trim()}>
          {pending ? '登录中…' : '进入看板'}
        </button>
      </form>
      <Toaster />
    </div>
  );
}

function BootScreen() {
  return (
    <div className="auth-wrap">
      <div className="auth-card auth-boot">
        <div className="auth-title">三省六部 · 连接中</div>
        <div className="auth-sub">正在检查看板认证与实时数据。</div>
      </div>
    </div>
  );
}

export default function App() {
  const activeTab = useStore((s) => s.activeTab);
  const setActiveTab = useStore((s) => s.setActiveTab);
  const liveStatus = useStore((s) => s.liveStatus);
  const countdown = useStore((s) => s.countdown);
  const loadAll = useStore((s) => s.loadAll);
  const authEnabled = useStore((s) => s.authEnabled);
  const isAuthenticated = useStore((s) => s.isAuthenticated);

  useEffect(() => {
    startPolling();
    return () => stopPolling();
  }, []);

  if (authEnabled === null) {
    return <BootScreen />;
  }

  if (authEnabled && !isAuthenticated) {
    return <AuthGate />;
  }

  const tasks = liveStatus?.tasks || [];
  const edicts = tasks.filter(isEdict);
  const activeEdicts = edicts.filter((t) => !isArchived(t));
  const sync = liveStatus?.syncStatus;
  const syncOk = sync?.ok;

  const tabBadge = (key: string): string => {
    if (key === 'edicts') return String(activeEdicts.length);
    if (key === 'sessions') return String(tasks.filter((t) => !isEdict(t)).length);
    if (key === 'memorials') return String(edicts.filter((t) => ['Done', 'Cancelled'].includes(t.state)).length);
    if (key === 'monitor') {
      const activeDepts = tasks.filter((t) => isEdict(t) && t.state === 'Doing').length;
      return activeDepts + '活跃';
    }
    return '';
  };

  return (
    <div className="wrap">
      <div className="hdr">
        <div>
          <div className="logo">三省六部 · 总控台</div>
          <div className="sub-text">OpenClaw Sansheng-Liubu Dashboard</div>
        </div>
        <div className="hdr-r">
          <span className={`chip ${syncOk ? 'ok' : syncOk === false ? 'err' : ''}`}>
            {syncOk ? '✅ 同步正常' : syncOk === false ? '❌ 服务器未启动' : '⏳ 连接中…'}
          </span>
          <span className="chip">{activeEdicts.length} 道旨意</span>
          <button className="btn-refresh" onClick={() => loadAll()}>
            ⟳ 刷新
          </button>
          <span style={{ fontSize: 11, color: 'var(--muted)' }}>⟳ {countdown}s</span>
        </div>
      </div>

      <div className="tabs">
        {TAB_DEFS.map((t) => (
          <div
            key={t.key}
            className={`tab ${activeTab === t.key ? 'active' : ''}`}
            onClick={() => setActiveTab(t.key)}
          >
            {t.icon} {t.label}
            {tabBadge(t.key) && <span className="tbadge">{tabBadge(t.key)}</span>}
          </div>
        ))}
      </div>

      {activeTab === 'edicts' && <EdictBoard />}
      {activeTab === 'approval' && <ApprovalPanel />}
      {activeTab === 'court' && <CourtDiscussion />}
      {activeTab === 'monitor' && <MonitorPanel />}
      {activeTab === 'relay' && <RelayArchivePanel />}
      {activeTab === 'officials' && <OfficialPanel />}
      {activeTab === 'models' && <ModelConfig />}
      {activeTab === 'skills' && <SkillsConfig />}
      {activeTab === 'sessions' && <SessionsPanel />}
      {activeTab === 'memorials' && <MemorialPanel />}
      {activeTab === 'templates' && <TemplatePanel />}
      {activeTab === 'morning' && <MorningPanel />}

      <TaskModal />
      <Toaster />
      <CourtCeremony />
    </div>
  );
}
