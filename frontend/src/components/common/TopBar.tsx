import { NavLink, useNavigate } from 'react-router-dom';
import { ROLE_LABELS } from '../../constants/enums';
import { useAuthStore } from '../../stores/auth';

const TABS = [
  { to: '/processes', label: '流程库' },
  { to: '/board', label: '值守看板' },
  { to: '/interventions', label: '接管队列' },
  { to: '/materials', label: '材料库' },
];

export default function TopBar() {
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const navigate = useNavigate();

  return (
    <header className="topbar">
      <div className="brand">
        <div className="brand-mark" />
        <div className="brand-text">
          <span className="brand-name">RPALOOP</span>
          <span className="brand-sub">苏城企服 · 政务 RPA 值守台</span>
        </div>
      </div>
      <nav className="nav-tabs">
        {TABS.map((tab) => (
          <NavLink key={tab.to} to={tab.to}
            className={({ isActive }) => `nav-tab ${isActive ? 'active' : ''}`}>
            {tab.label}
          </NavLink>
        ))}
      </nav>
      <div className="right flex align-center gap-12">
        <span className="chip">robot SU-BOT-01</span>
        <div className="user-chip">
          <div className="user-avatar">{user?.name?.slice(0, 1) || '?'}</div>
          <div>
            <div>{user?.name || '未登录'}</div>
            <div className="role">{user ? ROLE_LABELS[user.role] : ''}</div>
          </div>
          <button className="logout" type="button"
            onClick={() => { logout(); navigate('/login'); }}>
            退出
          </button>
        </div>
      </div>
    </header>
  );
}
