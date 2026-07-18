import { useEffect, useState } from "react";
import { Activity, Film, Music, PlusCircle, Sparkles, Wand2 } from "lucide-react";
import { getJson, getProject, postJson, uploadFiles } from "../api/client";
import { EngineeringPanel } from "../components/EngineeringPanel";
import { HighlightClips } from "../components/HighlightClips";
import { SkillLibrary } from "../components/SkillLibrary";
import { StyleSelector } from "../components/StyleSelector";
import { TimelinePreview } from "../components/TimelinePreview";
import { UploadPanel } from "../components/UploadPanel";
import { VideoPreview } from "../components/VideoPreview";

type Project = {
  project_id: string;
  aspect_ratio?: string;
  videos: string[];
  bgm?: string;
  reference?: string;
  reference_style?: Record<string, unknown>;
  candidate_clips: Clip[];
  beats?: Record<string, unknown>;
  timeline?: Record<string, unknown>;
  output?: string;
  enhanced_output?: string;
  render_history?: RenderHistoryItem[];
  status: string;
  progress: number;
};

type RenderHistoryItem = {
  version?: number;
  created_at?: string;
  video_url?: string;
  style_template?: string;
  score?: number;
  target_duration?: number;
  aspect_ratio?: string;
  timeline_items?: number;
  source_family_usage?: Record<string, number>;
  music_picture_score?: number;
};

type Clip = {
  source: string;
  start: number;
  end: number;
  highlight_score: number;
  face_ratio: number;
  sharpness_score: number;
  composition_score: number;
  atmosphere_score: number;
  recommended_usage: string;
  reason: string;
};

type EnhanceCapabilities = {
  topaz?: {
    available: boolean;
    hint?: string;
  };
};

const DONE_STATUSES = new Set(["done", "render_failed"]);
const ENHANCE_DONE_STATUSES = new Set(["enhanced", "enhance_failed"]);
const PROJECT_STORAGE_KEY = "ai-fancut-project-id";
const ASPECT_RATIOS = [
  { value: "9:16", label: "\u7ad6\u5c4f 9:16" },
  { value: "16:9", label: "\u6a2a\u5c4f 16:9" },
  { value: "4:3", label: "\u7ecf\u5178 4:3" },
];

export default function App() {
  const [projectId, setProjectId] = useState<string>("");
  const [videos, setVideos] = useState<File[]>([]);
  const [bgm, setBgm] = useState<File[]>([]);
  const [reference, setReference] = useState<File[]>([]);
  const [style, setStyle] = useState("korean_cool_white");
  const [aspectRatio, setAspectRatio] = useState("9:16");
  const [keepSourceFiles, setKeepSourceFiles] = useState(true);
  const [project, setProject] = useState<Project | null>(null);
  const [capabilities, setCapabilities] = useState<EnhanceCapabilities | null>(null);
  const [log, setLog] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getJson("/api/enhance/capabilities")
      .then((data) => setCapabilities(data))
      .catch(() => setCapabilities({ topaz: { available: false, hint: "无法读取高清修复能力" } }));
  }, []);

  useEffect(() => {
    const rememberedId = window.localStorage.getItem(PROJECT_STORAGE_KEY);
    const loader = rememberedId ? getProject(rememberedId) : getJson("/api/project/latest");
    loader
      .then((data: Project) => {
        setProject(data);
        setProjectId(data.project_id);
        setAspectRatio(data.aspect_ratio || "9:16");
        window.localStorage.setItem(PROJECT_STORAGE_KEY, data.project_id);
        setLog((items) => [`已恢复项目：${data.project_id}`, ...items]);
      })
      .catch(() => undefined);
  }, []);

  async function refresh(id = projectId) {
    if (!id) return null;
    const data = await getProject(id);
    setProject(data);
    setProjectId(data.project_id);
    setAspectRatio(data.aspect_ratio || "9:16");
    window.localStorage.setItem(PROJECT_STORAGE_KEY, data.project_id);
    return data as Project;
  }

  async function handleNewProject() {
    setBusy(true);
    try {
      const data = (await postJson("/api/project", {})) as Project;
      setProject(data);
      setProjectId(data.project_id);
      setAspectRatio(data.aspect_ratio || "9:16");
      setVideos([]);
      setBgm([]);
      setReference([]);
      window.localStorage.setItem(PROJECT_STORAGE_KEY, data.project_id);
      setLog([`\u5df2\u65b0\u5efa\u9879\u76ee\uff1a${data.project_id}`]);
    } catch (error) {
      setLog((items) => [`\u65b0\u5efa\u9879\u76ee\u5931\u8d25\uff1a${error instanceof Error ? error.message : String(error)}`, ...items]);
    } finally {
      setBusy(false);
    }
  }

  async function runStep<T>(label: string, action: () => Promise<T>): Promise<T> {
    setLog((items) => [`${label}...`, ...items]);
    const data = await action();
    setLog((items) => [`${label} 完成`, ...items]);
    return data;
  }

  async function waitForRender(id: string) {
    for (;;) {
      await new Promise((resolve) => window.setTimeout(resolve, 1800));
      const data = await refresh(id);
      if (!data) continue;
      if (DONE_STATUSES.has(data.status)) {
        if (data.status === "render_failed") {
          const renderError = typeof data.timeline?.render_error === "string" ? data.timeline.render_error : "请查看项目 timeline.render_error";
          throw new Error(`渲染失败：${renderError}`);
        }
        return data;
      }
    }
  }

  async function waitForEnhance(id: string) {
    for (;;) {
      await new Promise((resolve) => window.setTimeout(resolve, 1800));
      const data = await refresh(id);
      if (!data) continue;
      if (ENHANCE_DONE_STATUSES.has(data.status)) {
        if (data.status === "enhance_failed") {
          const enhanceError = typeof data.timeline?.enhance_error === "string" ? data.timeline.enhance_error : "请检查 Topaz 或高清修复配置";
          throw new Error(`高清修复失败：${enhanceError}`);
        }
        return data;
      }
    }
  }

  async function handleGenerate() {
    setBusy(true);
    try {
      let id = projectId;
      if (videos.length) {
        const uploaded = await runStep("上传素材视频", () => uploadFiles("/api/upload/videos", videos, id || undefined));
        id = uploaded.project_id;
        setProjectId(id);
        window.localStorage.setItem(PROJECT_STORAGE_KEY, id);
      }
      if (!id) throw new Error("请先上传至少一段视频");
      if (bgm.length) await runStep("上传 BGM", () => uploadFiles("/api/upload/bgm", bgm, id));
      if (reference.length) await runStep("上传参考视频", () => uploadFiles("/api/upload/reference", reference, id));
      await runStep("分析参考风格", () => postJson("/api/analyze/reference", { project_id: id }));
      await runStep("分析素材高光", () => postJson("/api/analyze/materials", { project_id: id }));
      await runStep("分析 BGM 节拍", () => postJson("/api/analyze/bgm", { project_id: id }));
      await runStep("生成剪辑 timeline", () =>
        postJson("/api/generate/timeline", { project_id: id, style_template: style, aspect_ratio: aspectRatio, use_llm: true })
      );
      await runStep("启动输出视频任务", () =>
        postJson("/api/render", { project_id: id, keep_original_audio: false, cleanup_sources: !keepSourceFiles })
      );
      await waitForRender(id);
      setLog((items) => ["输出视频完成", ...items]);
    } catch (error) {
      setLog((items) => [`失败：${error instanceof Error ? error.message : String(error)}`, ...items]);
    } finally {
      setBusy(false);
    }
  }

  async function handleEnhance(mode: "topaz" | "ffmpeg_hq") {
    const id = project?.project_id || projectId;
    if (!id) return;
    if (mode === "topaz" && !capabilities?.topaz?.available) {
      setLog((items) => ["失败：未检测到 Topaz，请先安装 Topaz Video AI 或配置 TOPAZ_COMMAND_TEMPLATE", ...items]);
      return;
    }
    setBusy(true);
    try {
      await runStep(mode === "topaz" ? "启动 Topaz 高清修复" : "启动内置高清修复", () =>
        postJson("/api/enhance", { project_id: id, mode, preset: "idol_stage_hq" })
      );
      await waitForEnhance(id);
      setLog((items) => ["高清修复完成", ...items]);
    } catch (error) {
      setLog((items) => [`失败：${error instanceof Error ? error.message : String(error)}`, ...items]);
    } finally {
      setBusy(false);
    }
  }

  const renderError = typeof project?.timeline?.render_error === "string" ? project.timeline.render_error : undefined;
  const enhanceError = typeof project?.timeline?.enhance_error === "string" ? project.timeline.enhance_error : undefined;

  return (
    <main>
      <header className="hero">
        <div>
          <span className="eyebrow">
            <Sparkles size={16} />
            AI Fancut MVP
          </span>
          <h1>颜值向饭圈卡点混剪 Demo</h1>
          <p>上传人物素材和 BGM，自动找高光镜头、贴节拍生成竖屏混剪。</p>
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
        <UploadPanel title="Step 2 上传 BGM / 视频提取背景音" accept=".mp3,.wav,.m4a,.aac,.flac,.mp4,.mov,.m4v" files={bgm} onChange={setBgm} />
        <UploadPanel title="Step 3 上传参考饭圈视频（可选）" accept=".mp4,.mov,.m4v" files={reference} onChange={setReference} />
        <StyleSelector value={style} onChange={setStyle} />
        <section className="panel">
          <div className="panelHeader">
            <h2>{"\u8f93\u51fa\u6bd4\u4f8b"}</h2>
          </div>
          <div className="segmented aspectSegmented">
            {ASPECT_RATIOS.map((ratio) => (
              <button key={ratio.value} className={aspectRatio === ratio.value ? "active" : ""} onClick={() => setAspectRatio(ratio.value)}>
                {ratio.label}
              </button>
            ))}
          </div>
        </section>
      </section>

      <section className="actionBand">
        <button className="primary" disabled={busy} onClick={handleGenerate}>
          <Wand2 size={18} />
          {busy ? "生成中" : "Step 5 点击生成"}
        </button>
        <button className="secondary" disabled={busy} onClick={handleNewProject}>
          <PlusCircle size={18} />
          {"\u65b0\u5efa\u9879\u76ee"}
        </button>
        <button className="secondary" disabled={!projectId || busy} onClick={() => refresh()}>
          <Activity size={18} />
          刷新项目
        </button>
        <label className="toggleOption">
          <input type="checkbox" checked={keepSourceFiles} onChange={(event) => setKeepSourceFiles(event.target.checked)} />
          <span>保留源素材，便于 CapCut 二次执行</span>
        </label>
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
        {project?.reference_style && <pre className="jsonPanel">{JSON.stringify(project.reference_style, null, 2)}</pre>}
      </section>

      {project && (
        <VideoPreview
          projectId={project.project_id}
          status={project.status}
          progress={project.progress}
          output={project.output}
          enhancedOutput={project.enhanced_output}
          renderHistory={project.render_history || []}
          renderError={renderError}
          enhanceError={enhanceError}
          busy={busy}
          topazAvailable={Boolean(capabilities?.topaz?.available)}
          topazHint={capabilities?.topaz?.hint}
          aspectRatio={project.aspect_ratio || aspectRatio}
          onEnhance={handleEnhance}
        />
      )}
      <EngineeringPanel projectId={project?.project_id || projectId} busy={busy} />
      <SkillLibrary />
      {project?.candidate_clips && <HighlightClips clips={project.candidate_clips} />}
      {project?.timeline && <TimelinePreview timeline={project.timeline as never} />}
    </main>
  );
}
