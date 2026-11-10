import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ROLE_HINTS, ROLE_LABELS } from '../constants/enums';
import { useAuthStore } from '../stores/auth';
import type { Role } from '../types';

const DEMO_ACCOUNTS: Array<{ email: string; role: Role }> = [
  { email: 'admin@rpaloop.io', role: 'admin' },
  { email: 'engineer@rpaloop.io', role: 'engineer' },
  { email: 'viewer@rpaloop.io', role: 'viewer' },
];

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const login = useAuthStore((state) => state.login);
  const [email, setEmail] = useState('engineer@rpaloop.io');
  const [password, setPassword] = useState('Demo@2026');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async (event?: React.FormEvent) => {
    event?.preventDefault();
    setLoading(true);
    setError('');
    try {
      await login(email, password);
      const from = (location.state as { from?: string } | null)?.from;
      navigate(from && from !== '/login' ? from : '/processes', { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : '登录失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <section className="login-left">
        <div>
          <div className="login-kicker">SUZHOU GOV-SERVICE OUTSOURCING · RPA OPS</div>
          <h1 className="login-title">
            政务材料录入
            <br />
            <em>录制回放</em>值守台
          </h1>
          <p className="login-desc">
            苏城企服 86 名办事员，为 200+ 苏州企业代办年报、资质、补贴与工商变更。
            本台把办事员在政务网/税务/网银的 30-80 个字段录入动作录制为可回放流程，
            用定位器稳健性评分提前发现「页面改版悄悄填错位置」，用 DAG 调度与异常接管
            保证无人值守批次失败可被发现、可被续跑。
          </p>
          <div className="login-facts">
            <div>
              <div className="login-fact-value">12</div>
              <div className="login-fact-label">类重复录入事项</div>
            </div>
            <div>
              <div className="login-fact-value">25min</div>
              <div className="login-fact-label">单次人工录入耗时</div>
            </div>
            <div>
              <div className="login-fact-value">9</div>
              <div className="login-fact-label">企业年报标准步骤</div>
            </div>
          </div>
        </div>
        <div className="tiny faint">
          值守机器人 SU-BOT-01 / SU-BOT-02 · 苏州政务外包值守台 A2 · 演示环境
        </div>
      </section>

      <section className="login-right">
        <form className="login-form" onSubmit={submit}>
          <div className="panel">
            <div className="panel-head">
              <div>
                <div className="panel-kicker">OPERATOR SIGN IN</div>
                <div className="panel-title">登录值守台</div>
              </div>
              <span className="chip warn right">DEMO</span>
            </div>
            <div className="panel-body stack">
              <label className="field">
                <span className="field-label">工作邮箱</span>
                <input className="input" type="email" value={email} autoComplete="username"
                  onChange={(event) => setEmail(event.target.value)} placeholder="name@rpaloop.io" />
              </label>
              <label className="field">
                <span className="field-label">密码</span>
                <input className="input" type="password" value={password} autoComplete="current-password"
                  onChange={(event) => setPassword(event.target.value)} placeholder="Demo@2026" />
              </label>
              {error ? <div className="banner">{error}</div> : null}
              <button className="btn btn-primary" type="submit" disabled={loading}
                style={{ width: '100%', paddingBlock: 10 }}>
                {loading ? '校验中…' : '进入值守台'}
              </button>
              <div className="tiny faint">统一密码 Demo@2026 · 三个角色权限不同（只读角色接管会返回 403）</div>
            </div>
          </div>
          <div>
            <div className="panel-kicker" style={{ marginBottom: 8 }}>演示账号（点击填入）</div>
            <div className="account-cards">
              {DEMO_ACCOUNTS.map((account) => (
                <button key={account.email} type="button" className="account-card"
                  onClick={() => { setEmail(account.email); setPassword('Demo@2026'); }}>
                  <span>
                    <span className="role">{ROLE_LABELS[account.role]}</span>
                    <span className="mono" style={{ marginLeft: 10 }}>{account.email}</span>
                  </span>
                  <span className="tiny faint">{ROLE_HINTS[account.role]}</span>
                </button>
              ))}
            </div>
          </div>
        </form>
      </section>
    </div>
  );
}
