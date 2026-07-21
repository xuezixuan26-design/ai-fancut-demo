# AI Fancut Demo

一个面向颜值向、舞台向和饭圈二创场景的 AI 辅助视频剪辑 MVP。项目使用 FastAPI + React，从用户上传的人物视频、BGM 和可选参考视频中筛选高光片段，生成贴合节拍的剪辑方案，并导出可预览、可复用的成片与工程数据。

> 本项目不换脸、不重塑五官，也不会生成不存在的人脸。AI 仅参与素材分析和剪辑规划，视频画面始终来自用户上传的素材。

## 核心能力

- 素材管理：上传多段人物视频、BGM 和可选参考视频
- 画面分析：抽帧、人脸检测、清晰度、亮度、构图与稳定性评分
- 音乐分析：使用 librosa 提取 tempo 和 beat，辅助卡点
- 剪辑规划：通过 OpenAI API 或本地规则生成结构化 `timeline.json`
- 自动渲染：使用 MoviePy 和 FFmpeg 完成裁剪、变速、拼接、转场、字幕、调色与音频混合
- 多画幅输出：支持竖屏 `9:16`、横屏 `16:9` 和经典 `4:3`
- 8 种风格模板：神颜卡点、韩系冷白、氛围电影、甜向安利、高能舞台、递进颜值、黑白揭晓和反差专场
- 工程化评估：批量生成候选时间线，通过 Harness 评分、对比和选优
- 审片与改稿：对成片进行规则化评估，并生成或应用修订版时间线
- 知识与记忆：压缩项目上下文，积累模板、Skill、人工反馈和评估结果
- 二次创作：导出 CapCut 动作数据和 HyperFrames 视觉包装预览
- 输出管理：保存渲染历史，并支持可选的视频增强流程

## 技术栈

| 层级 | 技术 |
| --- | --- |
| 前端 | React 19、TypeScript、Vite 6、Lucide React |
| API | FastAPI、Pydantic、Uvicorn |
| 视觉分析 | OpenCV、MediaPipe、NumPy |
| 音频分析 | librosa、SoundFile |
| 剪辑渲染 | MoviePy、FFmpeg |
| AI 规划 | OpenAI API（可选，本地规则可回退） |
| 部署 | Vercel（前端）、Docker/Render（后端） |

## 项目结构

```text
ai-fancut-demo/
├── backend/
│   ├── app/
│   │   ├── api/          # 上传、分析、时间线、渲染和工程化接口
│   │   ├── models/       # 请求、项目状态与时间线数据模型
│   │   ├── services/     # 分析、规划、渲染、评估和导出服务
│   │   └── skills/       # 可复用剪辑 Skill 注册表
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/components/   # 上传、风格、时间线、预览和工程面板
│   └── src/pages/App.tsx
├── storage/              # 运行时素材、中间结果与输出（不提交）
├── DEPLOYMENT.md
└── render.yaml
```

## 环境要求

- Python 3.10–3.12（推荐 3.11）
- Node.js 20+
- FFmpeg，可通过命令行直接执行 `ffmpeg`
- 可选：OpenAI API Key

MediaPipe 对 Python 版本较敏感。如果安装失败，建议使用 Python 3.11 创建独立虚拟环境。

## 快速开始

### 1. 启动后端

macOS / Linux：

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Windows PowerShell：

```powershell
cd backend
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

后端启动后可访问：

- 健康检查：`http://127.0.0.1:8000/health`
- Swagger API 文档：`http://127.0.0.1:8000/docs`

### 2. 启动前端

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Windows 可将复制命令替换为 `Copy-Item .env.example .env`。然后打开 `http://127.0.0.1:5173`。

### 3. 可选：启用 OpenAI 规划

编辑 `backend/.env`：

```env
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=gpt-4o-mini
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
OUTPUT_FPS=30
MAX_UPLOAD_MB=800
```

未配置 `OPENAI_API_KEY` 时，项目会自动使用本地规则规划器，基础流程仍可运行。

## 使用流程

1. 新建项目，上传 3–10 段人物视频。
2. 上传 BGM，或上传可提取背景音的视频。
3. 可选上传一个参考剪辑，用于提取基础节奏与风格特征。
4. 选择风格模板和输出比例。
5. 生成候选片段、节拍分析和剪辑时间线。
6. 渲染并预览最终视频。
7. 可选运行 Harness 对比候选版本，或使用审片与自动改稿功能继续迭代。
8. 按需导出 CapCut 动作数据或 HyperFrames 视觉包装。

## 主要 API

| 类别 | 接口 |
| --- | --- |
| 项目 | `POST /api/project`、`GET /api/project/{project_id}` |
| 上传 | `POST /api/upload/videos`、`POST /api/upload/bgm`、`POST /api/upload/reference` |
| 分析 | `POST /api/analyze/reference`、`POST /api/analyze/materials`、`POST /api/analyze/bgm` |
| 时间线 | `GET /api/skills`、`POST /api/generate/timeline` |
| 渲染 | `POST /api/render`、`GET /api/output/{project_id}` |
| 增强与历史 | `POST /api/enhance`、`GET /api/render/history/{project_id}` |
| 工程评估 | `POST /api/harness/run`、`POST /api/harness/preview-run`、`POST /api/harness/promote` |
| 审片改稿 | `POST /api/critic/run`、`POST /api/critic/revise` |
| 知识库 | `POST /api/context/compress`、`GET /api/kb/summary` |
| 视觉导出 | `POST /api/hyperframes/export`、`GET /api/hyperframes/preview/{project_id}` |

完整请求结构和实时接口清单以启动后的 `/docs` 为准。

## 运行时数据

项目素材和中间结果默认写入 `storage/`。常见内容包括：

```text
storage/
├── raw_videos/{project_id}/
├── bgm/{project_id}/
├── reference/{project_id}/
├── outputs/{project_id}/
├── projects/{project_id}/
└── knowledge_base/
```

项目状态目录可能包含：

- `reference_style.json`
- `frame_analysis.json`
- `candidate_clips.json`
- `beats.json`
- `timeline.json`
- `context_summary.json`
- `harness_report.json`

这些目录可能包含用户素材和生成视频，不应提交到公开仓库。

## 部署

- 前端：部署到 Vercel，项目根目录设为 `frontend/`
- 后端：使用 `backend/Dockerfile` 部署到 Render、Railway、Fly.io、ECS 或 VM
- 快速路径：仓库根目录提供 `render.yaml`，可创建 Render Blueprint
- 前端环境变量 `VITE_API_BASE` 必须指向已部署的后端地址
- 后端 `CORS_ORIGINS` 必须包含前端域名
- 生产环境应为 `storage/` 配置持久化磁盘或对象存储

更多信息见 [DEPLOYMENT.md](./DEPLOYMENT.md)。

## 当前限制

- 素材分析仍通过同步请求执行；渲染虽在 FastAPI 后台任务中运行，但尚未接入独立队列、重试和任务取消机制。
- 人脸检测、参考风格解析和自动裁切属于 MVP 实现，不等同于专业剪辑师的逐帧判断。
- 部分转场、光效和推拉运镜是简化实现，效果受素材分辨率和构图影响。
- 视频增强依赖本机或部署环境中的额外工具与模型，默认不保证可用。
- 当前未包含用户认证、项目级访问控制、任务取消和完善的存储清理策略。

## 下一步方向

- 引入 Celery、RQ 或独立任务服务，支持异步分析、进度查询和取消任务
- 使用人脸轨迹与主体跟踪改进多画幅智能裁切
- 增加素材去重、表情/姿态评分和舞台高能段检测
- 完善可视化时间线编辑和人工精调能力
- 接入对象存储、项目权限、限流、日志与可观测性
- 为模板、Skill 和渲染链路补充自动化回归测试

## 内容与隐私说明

请只处理你拥有使用权或已获得授权的素材，并遵守适用的平台规则、著作权与肖像权要求。不要将 API Key、用户上传素材、生成视频或运行时 `.env` 文件提交到公开仓库。

## License

仓库目前未包含开源许可证。如计划公开分发、接受外部贡献或用于商业场景，请先补充合适的 `LICENSE` 文件。
