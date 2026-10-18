# Cineva

> 一句话生成完整视频的 AI 创作工作台：剧本 → 角色/场景设计 → 分镜 → 参考图 → 视频生成 → 后期合成，六阶段全自动流水线。

**线上地址**：<https://cineva-studio.vercel.app>

---

## 项目简介

Cineva 是一个 AI 视频生成系统，把一个创作想法转化为完整视频。系统通过 6 个阶段的状态机推进，每个阶段由独立的 Agent 负责，支持在关键节点人工介入确认。

| 阶段 | Agent | 产出 |
|------|-------|------|
| 1. 剧本生成 | ScriptWriterAgent | 标题 / 风格 / 角色 / 布景 / 分镜脚本 |
| 2. 角色场景设计 | CharacterDesignerAgent | 角色与场景设定图 |
| 3. 分镜 | StoryboardAgent | 逐镜头分镜脚本 |
| 4. 参考图生成 | ReferenceGeneratorAgent | 关键帧参考图 |
| 5. 视频生成 | VideoDirectorAgent | 分镜视频片段 |
| 6. 后期合成 | VideoEditorAgent | 最终成片 |

前端提供首页创作坞、作品社区、技能库、资产页、临时工作台等完整产品界面；后端基于 FastAPI，负责任务编排、模型调用与会话持久化。

## 技术栈

**前端** `xiaoyunque/frontend/`
- Next.js（App Router）+ React + TypeScript
- Tailwind CSS + @xyflow/react（画布）+ lucide-react
- 部署：Vercel

**后端** `xiaoyunque/backend/`
- Python ≥ 3.10 + FastAPI + uvicorn
- 工作流编排引擎（`core/orchestrator.py`）+ 6 个阶段 Agent
- 模型接入：LLM / VLM / 文生图 / 文生视频（DashScope、DeepSeek、Gemini、Ark、Kling 等）
- 部署：Railway（Docker / nixpacks）

## 目录结构

```text
.
├── xiaoyunque/
│   ├── backend/          # FastAPI 后端
│   │   ├── api/          # REST API 路由与 schema
│   │   ├── core/         # 工作流引擎与 Agent 基类
│   │   ├── models/       # LLM / 图像 / 视频 / VLM 客户端
│   │   ├── pipelines/    # 流水线定义
│   │   ├── prompts/      # 提示词模板
│   │   ├── api_server.py # 服务入口
│   │   └── config.yaml.example
│   └── frontend/         # Next.js 前端
│       ├── app/          # 页面（App Router）
│       ├── components/   # 组件
│       ├── config/       # 场景 / 技能 / 作品配置
│       └── lib/          # API 客户端与本地存储
├── references/           # API 文档
├── SKILL.md              # OpenClaw Agent 工作流规则
└── CLAUDE.md             # 仓库协作指引
```

## 本地运行

### 后端

```bash
cd xiaoyunque/backend
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp config.yaml.example config.yaml   # 按需填入模型 Key
python api_server.py                  # 默认 http://127.0.0.1:8000
```

健康检查：

```bash
curl http://127.0.0.1:8000/api/health
```

### 前端

```bash
cd xiaoyunque/frontend
npm install
npm run dev        # 开发
# 或
npm run build && npm start   # 生产
```

默认 <http://localhost:3000>，通过环境变量 `BACKEND_API_URL` / `NEXT_PUBLIC_API_URL` 指向后端地址。

## 配置说明

- 模型密钥统一写入后端 `config.yaml`（已被 `.gitignore` 排除，不入库），参考 `config.yaml.example`。
- 前端通过 Vercel 环境变量配置后端地址。
- 部署所需的排除清单见 `backend/.railwayignore`、`backend/.dockerignore`、`frontend/.vercelignore`。

## 作者

**jokerking-oss** · 独立设计与开发

---

> 本仓库为个人作品项目。
