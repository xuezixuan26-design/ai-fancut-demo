import { useState } from "react";
import { Wand2, Activity, Film, Music, Sparkles } from "lucide-react";
import { getProject, postJson, uploadFiles } from "../api/client";
import { HighlightClips } from "../components/HighlightClips";
import { SkillLibrary } from "../components/SkillLibrary";
import { StyleSelector } from "../components/StyleSelector";
import { TimelinePreview } from "../components/TimelinePreview";
import { UploadPanel } from "../components/UploadPanel";
import { VideoPreview } from "../components/VideoPreview";

type Project = {
  project_id: string;
  videos: string[];
  bgm?: string;
  reference?: string;
  reference_style?: Record<string, unknown>;
  candidate_clips: [];
  beats?: Record<string, unknown>;
  timeline?: Record<string, unknown>;
  output?: string;
  status: string;
  progress: number;
};

export default function App() {
  const [projectId, setProjectId] = useState<string>("");
  const [videos, setVideos] = useState<File[]>([]);
  const [bgm, setBgm] = useState<File[]>([]);
  const [reference, setReference] = useState<File[]>([]);
  const [style, setStyle] = useState("korean_cool_white");
  const [project, setProject] = useState<Project | null>(null);
  const [log, setLog] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);

  async function refresh(id = projectId) {
    if (!id) return;
    const data = await getProject(id);
    setProject(data);
  }

  async function runStep<T>(label: string, action: () => Promise<T>): Promise<T> {
    setLog((items) => [`${label}...`, ...items]);
    const data = await action();
    setLog((items) => [`${label} 完成`, ...items]);
    return data;
  }

  async function handleGenerate() {
    setBusy(true);
    try {
      let id = projectId;
      if (videos.length) {
        const uploaded = await runStep("上传素材视频", () => uploadFiles("/api/upload/videos", videos, id || undefined));
        id = uploaded.project_id;
        setProjectId(id);
      }
      if (!id) throw new Error("请先上传至少一段视频");
      if (bgm.length) await runStep("上传 BGM", () => uploadFiles("/api/upload/bgm", bgm, id));
      if (reference.length) await runStep("上传参考视频", () => uploadFiles("/api/upload/reference", reference, id));
      await runStep("分析参考风格", () => postJson("/api/analyze/reference", { project_id: id }));
      await runStep("分析素材高光", () => postJson("/api/analyze/materials", { project_id: id }));
      await runStep("分析 BGM 节拍", () => postJson("/api/analyze/bgm?target_duration=30", { project_id: id }));
      await runStep("生成剪辑 timeline", () =>
        postJson("/api/generate/timeline", { project_id: id, style_template: style, target_duration: 30, use_llm: true })
      );
      await runStep("渲染 9:16 成片", () => postJson("/api/render", { project_id: id, keep_original_audio: false }));
      await refresh(id);
    } catch (error) {
      setLog((items) => [`失败：${error instanceof Error ? error.message : String(error)}`, ...items]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main>
      <header className="hero">
        <div>
          <span className="eyebrow">
            <Sparkles size={16} />
            AI Fancut MVP
          </span>
          <h1>颜值向饭圈卡点混剪 Demo</h1>
          <p>上传人物素材和 BGM，自动找高光镜头、贴拍点生成竖屏混剪。</p>
        </div>
        <div className="statusBox">
          <strong>{project?.status || "ready"}</strong>
          <div className="progress">
            <span style={{ width: `${project?.progress || 0}%` }} />
          </div>
          <small>{projectId || "新项目将在首次上传时创建"}</small>
        </div>
      </header>

      <section className="workflow">
        <UploadPanel title="Step 1 上传素材视频" accept=".mp4,.mov,.m4v" multiple files={videos} onChange={setVideos} />
        <UploadPanel title="Step 2 上传 BGM" accept=".mp3,.wav,.m4a,.aac,.flac,.mp4,.mov,.m4v" files={bgm} onChange={setBgm} />
        <UploadPanel title="Step 3 上传参考饭圈视频（可选）" accept=".mp4,.mov,.m4v" files={reference} onChange={setReference} />
        <StyleSelector value={style} onChange={setStyle} />
      </section>

      <section className="actionBand">
        <button className="primary" disabled={busy} onClick={handleGenerate}>
          <Wand2 size={18} />
          {busy ? "生成中" : "Step 5 点击生成"}
        </button>
        <button className="secondary" disabled={!projectId || busy} onClick={() => refresh()}>
          <Activity size={18} />
          刷新项目
        </button>
        <div className="badges">
          <span>
            <Film size={14} />
            {project?.videos?.length || videos.length} videos
          </span>
          <span>
            <Music size={14} />
            {project?.bgm || bgm[0]?.name || "BGM"}
          </span>
        </div>
      </section>

      <section className="results">
        <div className="logPanel">
          <h2>处理进度</h2>
          {log.length === 0 ? <p>等待开始</p> : log.map((item, index) => <p key={`${item}-${index}`}>{item}</p>)}
        </div>
        {project?.reference_style && (
          <pre className="jsonPanel">{JSON.stringify(project.reference_style, null, 2)}</pre>
        )}
      </section>

      <SkillLibrary />
      {project?.candidate_clips && <HighlightClips clips={project.candidate_clips} />}
      {project?.timeline && <TimelinePreview timeline={project.timeline as never} />}
      {project?.output && <VideoPreview projectId={project.project_id} />}
    </main>
  );
}
