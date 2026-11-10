import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { materialApi } from '../api/materials';
import { processApi } from '../api/processes';
import Panel from '../components/common/Panel';
import EmptyState from '../components/common/EmptyState';
import StatusLamp from '../components/common/StatusLamp';
import RunLaunchDialog from '../components/common/RunLaunchDialog';
import { MATTER_TYPE_LABELS, PROCESS_STATUS_LABELS } from '../constants/enums';
import { useAsync } from '../hooks/useAsync';
import { useAuthStore } from '../stores/auth';
import type { Material, ProcessItem } from '../types';
import { formatPercent } from '../utils/format';

const STATUS_TONE: Record<string, 'ok' | 'warn' | 'idle'> = {
  published: 'ok',
  draft: 'warn',
  archived: 'idle',
};

export default function ProcessListPage() {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const canOperate = user?.role === 'admin' || user?.role === 'engineer';
  const { data, loading, error } = useAsync(() => processApi.list(), []);
  const materialsState = useAsync(() => materialApi.list(), []);
  const [dialogProcess, setDialogProcess] = useState<ProcessItem | null>(null);
  const [message, setMessage] = useState('');

  const processes = data?.items ?? [];
  const materials: Material[] = materialsState.data?.items ?? [];
  const stats = useMemo(() => ({
    total: processes.length,
    published: processes.filter((item) => item.status === 'published').length,
    steps: processes.reduce((sum, item) => sum + item.step_count, 0),
    drafts: processes.filter((item) => item.status === 'draft').length,
  }), [processes]);

  const publish = async (process: ProcessItem) => {
    setMessage('');
    try {
      const result = await processApi.publish(process.id, '值守台发布');
      setMessage(`已发布「${result.process.name}」v${result.process.version}，历史版本 ${result.process.archived_versions.join(',') || '无'} 归档`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : '发布失败');
    }
  };

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <div className="crumb">流程录制 / 回放</div>
          <h1 className="page-title">流程库</h1>
          <p className="page-sub">
            4 类政务事项的录制回放流程；定位器稳健分由算法 A 按近 8 次运行命中记录重算，
            高风险步骤在编辑器内标红并可干跑校验。
          </p>
        </div>
        <div className="head-meta">
          <span className="chip">机器人 SU-BOT-01/02</span>
          <span className="chip warn">演示数据 · seed</span>
        </div>
      </header>

      <div className="stat-row" style={{ marginBottom: 18 }}>
        <div className="stat-cell">
          <div className="stat-value">{stats.total}</div>
          <div className="stat-label">流程</div>
        </div>
        <div className="stat-cell">
          <div className="stat-value green">{stats.published}</div>
          <div className="stat-label">已发布</div>
        </div>
        <div className="stat-cell">
          <div className="stat-value">{stats.steps}</div>
          <div className="stat-label">录制步骤</div>
        </div>
        <div className="stat-cell">
          <div className="stat-value amber">{stats.drafts}</div>
          <div className="stat-label">待发布草稿</div>
        </div>
      </div>

      {message ? <div className="banner warn" style={{ marginBottom: 14 }}>{message}</div> : null}
      {error ? <div className="banner" style={{ marginBottom: 14 }}>{error}</div> : null}

      <Panel kicker="PROCESS CATALOG" title="录制流程清单" tight>
        {loading ? (
          <div className="panel-body muted">加载流程…</div>
        ) : processes.length === 0 ? (
          <div className="panel-body">
            <EmptyState title="还没有录制流程" hint="以 JSON 步骤导入或从编辑器录入第一个流程。" />
          </div>
        ) : (
          <div className="rowlist">
            {processes.map((process) => (
              <div key={process.id} className="rowitem"
                style={{ gridTemplateColumns: '1.6fr 0.9fr 0.7fr 1.05fr 1.5fr' }}>
                <div>
                  <div className="row-title">{process.name}</div>
                  <div className="row-sub mono">v{process.version} · {process.owner}</div>
                </div>
                <div>
                  <span className="chip">{MATTER_TYPE_LABELS[process.matter_type]}</span>
                </div>
                <div>
                  <span className={`chip ${STATUS_TONE[process.status]}`}>
                    <StatusLamp tone={STATUS_TONE[process.status]} />
                    {PROCESS_STATUS_LABELS[process.status]}
                  </span>
                </div>
                <div>
                  <div className="tiny muted">{process.step_count} 步 · 成功率 {formatPercent(process.success_rate)}</div>
                  <div className="progress" style={{ marginTop: 6 }}>
                    <div className={`progress-fill ${process.success_rate >= 0.6 ? 'ok' : ''}`}
                      style={{ width: `${Math.round(process.success_rate * 100)}%` }} />
                  </div>
                </div>
                <div className="flex gap-8" style={{ justifyContent: 'flex-end' }}>
                  <button className="btn btn-sm" type="button"
                    onClick={() => navigate(`/processes/${process.id}/edit`)}>
                    步骤编辑器
                  </button>
                  {canOperate ? (
                    <button className="btn btn-primary btn-sm" type="button"
                      onClick={() => setDialogProcess(process)}>
                      发起运行
                    </button>
                  ) : (
                    <span className="chip">只读角色</span>
                  )}
                  {user?.role === 'admin' ? (
                    <button className="btn btn-sm" type="button" onClick={() => publish(process)}>
                      发布
                    </button>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        )}
      </Panel>

      {dialogProcess ? (
        <RunLaunchDialog process={dialogProcess} materials={materials}
          onClose={() => setDialogProcess(null)} />
      ) : null}
    </div>
  );
}
