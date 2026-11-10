# rpaloop · 政务材料录入 RPA 录制回放台

苏城企服（苏州政务外包公司，86 人）的政务材料录入 RPA 值守台：把办事员在政务网/税务/网银的
30-80 个字段录入动作录制为流程并回放，用**定位器稳健性评分**提前发现「页面改版后旧脚本悄悄填错位置」，
用**步骤 DAG 调度 + 断点续跑 + 异常接管**保证无人值守批次失败可被发现、可续跑、可导出审计报告。

## 真实场景

- **模拟客户**：苏城企服，86 名办事员，服务 200+ 苏州企业（年报、高企资质、稳岗补贴、工商变更）。
- **现有工作流**：办事员登录政务网逐字段手工录入，单次 25 分钟，完成后截图留证放共享盘。
- **3 个痛点**：① 12 类事项重复录入、人工易错；② 页面改版后旧脚本定位全挂却不报错（填错位置）；
  ③ 无人值守批次失败无人知晓，第 3 天才发现材料过期。
- **上下游**：上游=企业档案/材料清单（材料库 + GB 32100 信用代码校验）→ 本系统替代「流程录制、
  定位器评分、无人值守执行、异常接管」→ 下游=申报回执、审计留档（执行报告 CSV/Markdown 导出）。

## 角色与权限

| 账号 | 密码 | 角色 | 权限 | 典型动作 |
|---|---|---|---|---|
| `admin@rpaloop.io` | `Demo@2026` | 平台管理员 | 全部 | 发布流程新版本、归档旧版、材料库维护 |
| `engineer@rpaloop.io` | `Demo@2026` | 值守操作员 | 执行、干跑、接管处理；**不能发布流程版本** | 干跑、重试接管、取消 run |
| `viewer@rpaloop.io` | `Demo@2026` | 审计只读 | 只读 + 导出报告；**接管 403** | 导出执行报告 |

权限在后端 FastAPI 依赖（`require_roles`）强制校验，前端仅按角色隐藏按钮。

## 快速启动

```bash
cp .env.example .env          # 按需修改端口/密码
docker compose config --quiet # 校验 compose
docker compose up -d --build  # 首次构建约 2-4 分钟
docker compose ps             # 等 5/5 healthy
```

- 前端：<http://localhost:18237>
- 后端 API 文档：<http://localhost:19237/api/docs>
- 健康检查：`curl http://localhost:19237/api/health`

`SEED_DEMO=true` 时后端启动自动执行一次 seed（幂等），也可手动：

```bash
docker compose exec backend python -m scripts.seed_demo
# SEED_SUMMARY brand=rpaloop processes=4 steps=32 materials=6 runs=8 runsteps=45 interventions=3 users=3
```

## 核心功能

| 页面 | 路径 | 说明 |
|---|---|---|
| 登录 | `/login` | 三角色演示账号，一键填入 |
| 流程库 | `/processes` | 4 个流程（年报 9 步 / 资质 7 步 / 补贴 8 步 / 变更 8 步） |
| 步骤编辑器 | `/processes/:id/edit` | 左侧步骤灯列 + 右侧定位器候选与稳健分、断言/重试配置、干跑 |
| 值守看板 | `/board` | 队列、进行中 run 步骤灯、失败高亮，2s 轮询 |
| 运行详情 | `/runs/:id` | 步骤时间线、命中定位器、幂等键、接管记录、日志、报告导出 |
| 接管队列 | `/interventions` | 重试 / 改定位器 / 跳过 / 终止；viewer 403 |
| 材料库 | `/materials` | GB 32100 信用代码校验位真算，2 条非法标红且不能发起申报 |

## 核心算法

### 算法 A：定位器稳健性评分 `backend/src/services/locator_score.py`

- **输入**：步骤 `locator_candidates`（strategy + selector）+ 该步骤近 8 次 `RunStep` 命中记录
  （`locator_used` / `attempt` / `status`）。
- **指标**：`hit_rate`=命中次数/历史样本；`avg_attempt_score`=1/avg_attempts；
  `specificity`=策略基准分(0.85 id / 0.80 text / 0.75 role / 0.55 css / 0.35 xpath)
  − 层级深度惩罚 − 选择器长度惩罚；`dynamic_risk`=正则检出 `\d{4,}`、uuid、时间戳、hash → 1.0。
- **公式**：`score = 100·(0.45·hit_rate + 0.20·avg_attempt_score + 0.20·(1−dynamic_risk) + 0.15·specificity)`。
- **输出**：每候选分、推荐主/备定位器、步骤稳健分与风险等级（high/medium/low）+ 原因，全部落库
  `steps.locator_scores / robustness_score / risk_level / risk_reason`。
- **失败态**：无历史 → `score=50`, `reason=no_history`（seed 中变更流程即为此态）。
- **可复现**：`POST /api/processes/{id}/rescore` 按当前历史确定重算。

### 算法 B：步骤 DAG 调度 + 断点续跑 / 失败接管 `backend/src/services/executor.py`

- **DAG**：步骤 `depends_on`（空=链式依赖 seq-1）→ Kahn 拓扑排序，执行序列落库 `runs.execution_sequence`。
- **幂等键**：`sha256(run_id + step_id + material.credit_code)`；续跑时已成功且幂等键一致的步骤跳过，
  跳过集合落库 `runs.skipped_steps`。
- **失败分类**：transient(timeout/network) → 指数退避 1/2/4s 至 `max_retries`；
  `assert_failed`/`locator_drift` → 生成 `Intervention` 并把 run 置为 `takeover` 暂停。
- **并发**：同一 Material 同时仅允许 1 个进行中的 run —— `runs.active_lock` 唯一约束 + 材料行锁，
  冲突返回 409 `E_CONCURRENCY_CONFLICT`。
- **可复现**：`dry_run` 不真实等待；assert 失败由 `Material.missing_flags` 固定触发。
- **执行器**：Celery worker（Redis broker）消费 `rpaloop.execute_run`，逐步骤记录
  `run_steps`（attempt/耗时/命中定位器/错误码/幂等键/output_digest）。

### GB 32100 统一社会信用代码校验 `backend/src/utils/credit_code.py`

字符集 31 位（0-9 + A-Z 去掉 I/O/S/V/Z）；前 17 位按权重 `[1,3,9,27,19,26,16,17,20,29,25,13,8,24,10,30,28]`
加权求和取模 31，`check = 31 − (sum mod 31)`（31→0），与第 18 位比对。seed 中 2 家企业（华泰针织、信德模塑）校验位不匹配。

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | React 18 + TypeScript + Vite + Zustand + React Router 6，Nginx 托管 dist |
| 后端 | Python 3.11 + FastAPI 0.115 + SQLAlchemy 2.0（同步）+ Pydantic v2 + PyJWT + Passlib |
| 异步 | Celery 5.4 + Redis 7（broker/backend），worker 执行 run |
| 数据库 | MySQL 8.0（utf8mb4），Alembic 迁移 |
| 部署 | Docker Compose，5 服务（frontend/backend/worker/db/redis），全部 healthcheck |

## 目录结构

```
gb-564/
├── docker-compose.yml          # 5 服务 + 命名卷 + 5 个 healthcheck
├── .env / .env.example
├── backend/
│   ├── Dockerfile / Dockerfile.worker / entrypoint.sh / requirements.txt
│   ├── alembic.ini / migrations/
│   ├── scripts/seed_demo.py
│   └── src/{config,constants,models,schemas,services,controllers,routes,middlewares,utils}
└── frontend/
    ├── Dockerfile / nginx.conf
    └── src/{api,stores,types,components/common,components/business,hooks,pages,router,utils,constants,styles}
```

## 枚举出现位置（前后端各一份）

| 枚举 | 后端 | 前端 |
|---|---|---|
| UserRole | `backend/src/constants/enums.py` `roles.py` | `frontend/src/constants/enums.ts` `types/index.ts` |
| MatterType / ProcessStatus | `backend/src/constants/enums.py` | `frontend/src/constants/enums.ts` |
| StepAction / StepStatus | `backend/src/constants/enums.py` | `frontend/src/constants/enums.ts` |
| RunStatus / RunTrigger / RunStepStatus | `backend/src/constants/enums.py` `models/run*.py` | `frontend/src/constants/enums.ts` `types/index.ts` |
| InterventionReason / InterventionStatus | `backend/src/constants/enums.py` `models/intervention.py` | `frontend/src/constants/enums.ts` |
| RiskLevel | `backend/src/constants/enums.py` `locator_score.py` | `frontend/src/constants/enums.ts` `utils/risk.ts` |

## 环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `COMPOSE_PROJECT_NAME` | rpaloop | 容器名前缀 |
| `FRONTEND_PORT` / `BACKEND_PORT` / `DB_PORT` | 18237 / 19237 / 17737 | 宿主端口 |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_ROOT_PASSWORD` | rpaloop / rpaloop / … | MySQL |
| `JWT_SECRET` / `JWT_EXPIRE_MINUTES` | demo / 720 | JWT 签名 |
| `REDIS_URL` | redis://redis:6379/0 | Celery broker |
| `SEED_DEMO` | true | 启动自动 seed |
| `RATE_LIMIT_PER_MINUTE` | 240 | 限流中间件阈值 |

## Docker 说明

- 5 服务全部带 healthcheck：db（mysqladmin ping）、redis（redis-cli ping）、backend（curl /api/health）、
  worker（celery inspect ping）、frontend（wget 首页）。
- 依赖顺序：db/redis healthy → backend healthy → worker/frontend。
- 命名卷：`db_data`（MySQL）、`redis_data`（Redis AOF）、`shared_artifacts`（backend/worker 共享产物目录）。
- 停止并清理：`docker compose down -v --remove-orphans`。

## 本地开发

```bash
# 后端（需本机 MySQL/Redis，或仅用容器 db/redis）
cd backend && pip install -r requirements.txt
DB_HOST=127.0.0.1 DB_PORT=17737 uvicorn src.main:app --reload --port 19237
# worker
celery -A src.config.celery_app worker -l info --concurrency=2
# 前端
cd frontend && npm install --registry=https://registry.npmjs.org && npm run dev
```

## License

MIT（演示项目，数据均为虚构）。
