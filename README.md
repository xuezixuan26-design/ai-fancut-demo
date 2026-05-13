# AI 颜值向饭圈二创视频剪辑 Demo

这是一个 FastAPI + React 的 MVP，用来演示从用户上传的人物视频素材和 BGM 中自动生成 9:16 竖屏颜值向卡点混剪。

系统不会换脸、不会重塑五官、不会生成不存在的人脸。它只从用户上传素材中筛选清晰、近景、构图较好的片段，并完成剪辑、卡点、基础转场、字幕、调色和导出。

## 功能

- 多段视频素材上传，保存到 `storage/raw_videos`
- BGM 上传，保存到 `storage/bgm`
- 可选参考视频上传，保存到 `storage/reference`
- OpenCV + MediaPipe 抽帧、人脸检测、清晰度、亮度、构图和稳定性评分
- librosa 分析 BGM tempo 和 beat
- OpenAI API 生成剪辑计划 JSON；未配置 `OPENAI_API_KEY` 时自动使用本地规划器
- MoviePy 裁剪、变速、拼接、加 BGM
- FFmpeg 调色、ASS 字幕烧录、H.264/AAC 导出 MP4
- React 页面展示上传列表、进度、高光片段、timeline 和最终视频

## 环境要求

- Python 3.10-3.12 推荐
- Node.js 20+
- FFmpeg，需要在命令行中可直接执行 `ffmpeg`
- 可选：`OPENAI_API_KEY`

> MediaPipe 对 Python 版本比较敏感。如果你的 Python 版本过新，建议创建 Python 3.11 虚拟环境。

## 后端运行

```bash
cd ai-fancut-demo/backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
set OPENAI_API_KEY=你的_key
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

不配置 `OPENAI_API_KEY` 也能跑通，系统会使用本地规则生成 `timeline.json`。

## 前端运行

```bash
cd ai-fancut-demo/frontend
npm install
npm run dev
```

打开 `http://localhost:5173`。

## Demo 使用步骤

1. 上传 3-10 段人物视频素材。
2. 上传 1 个 BGM。
3. 可选上传参考饭圈剪辑视频。
4. 选择一个风格模板。
5. 点击生成。
6. 页面会展示参考风格、候选高光片段、timeline 和最终成片预览。

## API 流程

```text
POST /api/upload/videos
POST /api/upload/bgm
POST /api/upload/reference
POST /api/analyze/reference
POST /api/analyze/materials
POST /api/analyze/bgm
POST /api/generate/timeline
POST /api/render
GET  /api/project/{project_id}
GET  /api/output/{project_id}
```

每个项目的中间 JSON 会写入 `storage/projects/{project_id}`：

- `reference_style.json`
- `frame_analysis.json`
- `candidate_clips.json`
- `beats.json`
- `timeline.json`

## 当前限制

- 自动裁切第一版默认中心裁切，后续可以用逐片段人脸中心做动态裁切。
- 参考视频风格解析使用帧差和基础统计，适合 Demo，不等同专业镜头语言识别。
- 闪白、光晕、慢推近是简化实现。
- LLM 只负责规划 JSON，不接触视频帧，也不做任何人脸生成或美颜重塑。
- 长视频分析和渲染耗时较长，第一版使用同步接口，后续建议接队列和任务进度。

## 后续扩展

- 引入 Celery/RQ 做异步任务和可取消渲染
- 用人脸轨迹做 9:16 智能裁切
- 接 Remotion 做复杂花字和动态包装
- 加可视化时间线编辑
- 增加镜头去重、表情识别、姿态评分和舞台高能段检测
