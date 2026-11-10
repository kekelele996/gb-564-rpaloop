import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { materialApi, type CreditCheck } from '../api/materials';
import EmptyState from '../components/common/EmptyState';
import Panel from '../components/common/Panel';
import StatusLamp from '../components/common/StatusLamp';
import { useAsync } from '../hooks/useAsync';
import type { Material } from '../types';
import { formatDate } from '../utils/format';

export default function MaterialsPage() {
  const navigate = useNavigate();
  const { data, loading, error } = useAsync(() => materialApi.list(), []);
  const [checks, setChecks] = useState<Record<number, CreditCheck>>({});
  const [busyId, setBusyId] = useState<number | null>(null);
  const [message, setMessage] = useState('');

  const materials: Material[] = data?.items ?? [];
  const invalid = materials.filter((item) => !item.credit_valid);
  const withMissing = materials.filter((item) => item.missing_flags.length > 0);

  const check = async (material: Material) => {
    setBusyId(material.id);
    setMessage('');
    try {
      const result = await materialApi.creditCheck(material.id);
      setChecks((prev) => ({ ...prev, [material.id]: result }));
      setMessage(result.valid
        ? `${material.company_name} 校验位通过，可发起申报`
        : `${material.company_name} 校验失败：${result.reason}`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : '校验失败');
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <div className="crumb">ENTITY MATERIALS · GB 32100</div>
          <h1 className="page-title">企业材料库</h1>
          <p className="page-sub">
            6 家苏州企业的申报材料档案。统一社会信用代码按 GB 32100-2015 校验位算法真算：
            字符集 31 位加权求和后取模 31 推导校验位；校验失败的档案标红且不能发起申报。
          </p>
        </div>
        <div className="head-meta">
          <span className="chip danger">校验失败 {invalid.length}</span>
          <span className="chip warn">材料缺失 {withMissing.length}</span>
        </div>
      </header>

      <div className="stat-row" style={{ marginBottom: 18 }}>
        <div className="stat-cell">
          <div className="stat-value">{materials.length}</div>
          <div className="stat-label">企业材料档案</div>
        </div>
        <div className="stat-cell">
          <div className="stat-value green">{materials.length - invalid.length}</div>
          <div className="stat-label">信用代码有效</div>
        </div>
        <div className="stat-cell">
          <div className="stat-value red">{invalid.length}</div>
          <div className="stat-label">校验位不通过</div>
        </div>
        <div className="stat-cell">
          <div className="stat-value amber">{withMissing.length}</div>
          <div className="stat-label">存在缺失材料</div>
        </div>
      </div>

      {message ? <div className="banner warn" style={{ marginBottom: 14 }}>{message}</div> : null}
      {error ? <div className="banner" style={{ marginBottom: 14 }}>{error}</div> : null}

      <Panel kicker="CREDIT CODE REGISTRY" title="材料档案与信用代码校验" tight>
        {loading ? <div className="panel-body muted">加载材料库…</div> : materials.length === 0 ? (
          <div className="panel-body">
            <EmptyState title="材料库为空" hint="管理员可从企业档案导入材料清单。" />
          </div>
        ) : (
          <div className="rowlist">
            {materials.map((material) => {
              const checkResult = checks[material.id];
              const valid = checkResult ? checkResult.valid : material.credit_valid;
              const reason = checkResult ? checkResult.reason : material.credit_reason;
              return (
                <div key={material.id} className="rowitem"
                  style={{ gridTemplateColumns: '1.5fr 1.5fr 1.2fr 1.1fr 1.3fr' }}>
                  <div>
                    <div className="row-title">
                      {material.company_name}
                      {!valid ? <span style={{ color: 'var(--red)', marginLeft: 8 }}>●</span> : null}
                    </div>
                    <div className="row-sub">{material.contact}</div>
                  </div>
                  <div>
                    <div className="mono tiny" style={{ color: valid ? 'var(--text)' : 'var(--red)' }}>
                      {material.credit_code}
                    </div>
                    <div className={valid ? 'inline-ok' : 'inline-error'} style={{ marginTop: 4 }}>
                      <StatusLamp tone={valid ? 'ok' : 'danger'} />
                      {valid ? '校验位通过' : reason}
                      {checkResult ? <span className="tiny faint"> · 刚刚复算</span> : null}
                    </div>
                  </div>
                  <div>
                    <div className="tiny muted">有效期至</div>
                    <div className="tiny mono">{formatDate(material.validity_date)}</div>
                  </div>
                  <div>
                    <div className="tiny muted">附件（{material.attachments.length}）</div>
                    <div className="flex gap-8" style={{ flexWrap: 'wrap', marginTop: 4 }}>
                      {material.attachments.map((item) => <span key={item} className="chip">{item}</span>)}
                      {material.missing_flags.map((flag) => (
                        <span key={flag} className="chip danger">{flag.replace('attachment:', '缺失 ')}</span>
                      ))}
                    </div>
                  </div>
                  <div className="flex gap-8" style={{ justifyContent: 'flex-end', flexWrap: 'wrap' }}>
                    <button className="btn btn-sm" type="button" disabled={busyId === material.id}
                      onClick={() => check(material)}>
                      {busyId === material.id ? '复算中…' : '校验位复算'}
                    </button>
                    <button className="btn btn-primary btn-sm" type="button" disabled={!valid}
                      title={valid ? '前往流程库选择流程发起申报' : `信用代码校验失败：${reason}`}
                      onClick={() => navigate('/processes')}>
                      发起申报
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </Panel>
    </div>
  );
}
