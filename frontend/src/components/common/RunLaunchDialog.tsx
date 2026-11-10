import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { runApi } from '../../api/runs';
import type { Material, ProcessItem, RunItem } from '../../types';

interface Props {
  process: ProcessItem;
  materials: Material[];
  onClose: () => void;
}

export default function RunLaunchDialog({ process, materials, onClose }: Props) {
  const navigate = useNavigate();
  const usable = materials.filter((item) => item.credit_valid);
  const [materialId, setMaterialId] = useState<number>(usable[0]?.id ?? materials[0]?.id ?? 0);
  const [trigger, setTrigger] = useState<'dry_run' | 'manual'>('dry_run');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const start = async () => {
    if (!materialId) {
      setError('请选择企业材料');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const run: RunItem = await runApi.create(process.id, materialId, trigger);
      navigate(`/runs/${run.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : '发起运行失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <div className="panel modal">
        <header className="panel-head">
          <div>
            <div className="panel-kicker">LAUNCH ROBOT RUN</div>
            <div className="panel-title">{process.name} · v{process.version}</div>
          </div>
          <button className="btn btn-ghost btn-sm right" type="button" onClick={onClose}>关闭</button>
        </header>
        <div className="modal-body">
          <label className="field">
            <span className="field-label">企业材料（信用代码须通过 GB 32100 校验）</span>
            <select className="select" value={materialId} onChange={(event) => setMaterialId(Number(event.target.value))}>
              {materials.map((item) => (
                <option key={item.id} value={item.id} disabled={!item.credit_valid}>
                  {item.company_name} · {item.credit_code}
                  {item.credit_valid ? '' : '（校验失败）'}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span className="field-label">触发方式</span>
            <select className="select" value={trigger}
              onChange={(event) => setTrigger(event.target.value as 'dry_run' | 'manual')}>
              <option value="dry_run">干跑校验（不真实等待，验证步骤可达）</option>
              <option value="manual" disabled={process.status !== 'published'}>
                正式运行{process.status !== 'published' ? '（草稿流程不可正式运行）' : ''}
              </option>
            </select>
          </label>
          {trigger === 'manual' ? (
            <div className="banner warn">
              正式运行会占用该企业材料的并发锁：同一材料同一时间只允许 1 个进行中的 run。
            </div>
          ) : null}
          {error ? <div className="banner">{error}</div> : null}
        </div>
        <div className="modal-foot">
          <button className="btn btn-ghost" type="button" onClick={onClose}>取消</button>
          <button className="btn btn-primary" type="button" onClick={start} disabled={loading}>
            {loading ? '下发中…' : trigger === 'dry_run' ? '开始干跑' : '下发机器人'}
          </button>
        </div>
      </div>
    </div>
  );
}
