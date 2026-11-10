import type { MatterType, ProcessStatus, RiskLevel, Role, RunStatus, RunStepStatus, RunTrigger, StepAction } from '../types';

export const ROLE_LABELS: Record<Role, string> = {
  admin: '平台管理员',
  engineer: '值守操作员',
  viewer: '审计只读',
};

export const ROLE_HINTS: Record<Role, string> = {
  admin: '流程发布/归档、材料库、机器人配置',
  engineer: '执行、干跑、接管处理；不能发布版本',
  viewer: '只读 + 导出报告；接管 403',
};

export const MATTER_TYPE_LABELS: Record<MatterType, string> = {
  annual_report: '企业年报',
  qualification: '资质认定',
  subsidy: '补贴申报',
  change: '工商变更',
};

export const PROCESS_STATUS_LABELS: Record<ProcessStatus, string> = {
  draft: '草稿',
  published: '已发布',
  archived: '已归档',
};

export const RUN_STATUS_LABELS: Record<RunStatus, string> = {
  queued: '排队中',
  running: '执行中',
  succeeded: '已成功',
  failed: '已失败',
  cancelled: '已取消',
  takeover: '待接管',
};

export const RUN_TRIGGER_LABELS: Record<RunTrigger, string> = {
  manual: '手动',
  schedule: '定时值守',
  dry_run: '干跑校验',
};

export const RUN_STEP_STATUS_LABELS: Record<RunStepStatus, string> = {
  ok: '通过',
  retried: '重试通过',
  failed: '失败',
  skipped: '跳过',
};

export const STEP_ACTION_LABELS: Record<StepAction, string> = {
  click: '点击',
  input: '录入',
  upload: '上传',
  assert: '断言',
  wait: '等待',
};

export const RISK_LEVEL_LABELS: Record<RiskLevel, string> = {
  low: '低风险',
  medium: '中风险',
  high: '高风险',
};

export const INTERVENTION_REASON_LABELS: Record<string, string> = {
  assert_failed: '断言失败',
  locator_drift: '定位漂移',
  timeout: '执行超时',
  manual: '人工标记',
};

export const INTERVENTION_STATUS_LABELS: Record<string, string> = {
  open: '待接管',
  retrying: '重试中',
  resolved: '已解决',
  skipped: '已跳过',
  aborted: '已终止',
};

export const INTERVENTION_ACTIONS = [
  { value: 'retry', label: '重试', hint: '材料已补录 / 人工核验后放行本步骤并续跑' },
  { value: 'relocate', label: '改定位器', hint: '选择备选定位器后重试' },
  { value: 'skip', label: '跳过', hint: '标记本步骤跳过，继续执行后续步骤' },
  { value: 'abort', label: '终止', hint: '终止本次运行，已提交步骤记录补偿清单' },
] as const;

export const POLL_INTERVALS = { board: 2000, run: 2000, interventions: 3000 };
