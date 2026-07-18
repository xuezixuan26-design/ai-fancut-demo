import { Download, FileJson, Sparkles } from "lucide-react";
import { configuredApiBase } from "../api/client";

type Props = {
  projectId?: string;
  status?: string;
  progress?: number;
  output?: string;
  enhancedOutput?: string;
  renderHistory?: RenderHistoryItem[];
  renderError?: string;
  enhanceError?: string;
  busy?: boolean;
  topazAvailable?: boolean;
  topazHint?: string;
  aspectRatio?: string;
  onEnhance?: (mode: "topaz" | "ffmpeg_hq") => void;
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

const statusText: Record<string, string> = {
  created: "已创建项目",
  ready: "等待开始",
  videos_uploaded: "素材已上传",
  bgm_uploaded: "BGM 已上传",
  reference_uploaded: "参考视频已上传",
  reference_analyzed: "参考风格已分析",
  materials_analyzed: "素材高光已分析",
  bgm_analyzed: "BGM 节拍已分析",
  timeline_generated: "剪辑时间线已生成",
  rendering: "正在渲染成片",
  done: "成片已生成",
  enhancing: "正在高清修复",
  enhanced: "高清修复完成",
  render_failed: "渲染失败",
  enhance_failed: "高清修复失败",
};

function cssAspectRatio(value?: string) {
  if (value === "16:9") return "16 / 9";
  if (value === "4:3") return "4 / 3";
  return "9 / 16";
}

export function VideoPreview({
  projectId,
  status = "ready",
  progress = 0,
  output,
  enhancedOutput,
  renderHistory = [],
  renderError,
  enhanceError,
  busy,
  topazAvailable,
  topazHint,
  aspectRatio,
  onEnhance,
}: Props) {
  if (!projectId) return null;

  const url = `/api/output/${projectId}`;
  const enhancedUrl = `/api/enhanced-output/${projectId}`;
  const capcutUrl = `/api/capcut/actions/${projectId}`;
  const assetUrl = (path: string) => `${configuredApiBase()}${path}`;
  const hasOutput = Boolean(output);
  const done = status === "done" || status === "enhanced" || Boolean(output);
  const canExportActions = !["created", "ready"].includes(status);
  const isEnhancing = status === "enhancing";
  const latestHistory = [...renderHistory].sort((a, b) => Number(b.version || 0) - Number(a.version || 0)).slice(0, 6);

  return (
    <section className="previewPanel">
      <div className="panelHeader">
        <h2>输出结果</h2>
        <div className="panelActions">
          {canExportActions && (
            <a className="iconButton" href={assetUrl(capcutUrl)} download>
              <FileJson size={16} />
              CapCut 动作
            </a>
          )}
          {hasOutput && (
            <>
              {topazAvailable && (
                <button
                  className="iconButton"
                  disabled={busy || isEnhancing}
                  title={topazHint || "使用 Topaz Video AI 修复"}
                  onClick={() => onEnhance?.("topaz")}
                >
                  <Sparkles size={16} />
                  Topaz 修复
                </button>
              )}
              <button className="iconButton" disabled={busy || isEnhancing} onClick={() => onEnhance?.("ffmpeg_hq")}>
                <Sparkles size={16} />
                内置高清
              </button>
              <a className="iconButton" href={assetUrl(url)} download>
                <Download size={16} />
                下载成片
              </a>
            </>
          )}
          {enhancedOutput && (
            <a className="iconButton primaryLink" href={assetUrl(enhancedUrl)} download>
              <Download size={16} />
              下载高清版
            </a>
          )}
        </div>
      </div>
      <div className="outputStatus">
        <strong>{statusText[status] || status}</strong>
        <div className="progress">
          <span style={{ width: `${progress}%` }} />
        </div>
        <small>
          {enhancedOutput
            ? "高清修复版已生成，可以下载对比。"
            : topazAvailable
              ? "可以继续做 Topaz 或内置高清修复；修复版会单独保存，不覆盖原片。"
              : "当前使用内置高清修复；Topaz 作为后续外部增强能力预留。"}
        </small>
        {renderError && <p className="errorText">{renderError}</p>}
        {enhanceError && <p className="errorText">{enhanceError}</p>}
      </div>
      {done && <video className="videoPreview" style={{ aspectRatio: cssAspectRatio(aspectRatio) }} src={assetUrl(enhancedOutput ? enhancedUrl : url)} controls />}
      {latestHistory.length ? (
        <div className="renderHistoryList">
          <strong>渲染历史</strong>
          {latestHistory.map((item) => (
            <a className="renderHistoryItem" key={item.version} href={assetUrl(item.video_url || `/api/render/history/${projectId}/${item.version}`)} target="_blank" rel="noreferrer">
              <span>v{String(item.version || 0).padStart(3, "0")}</span>
              <small>
                {item.style_template || "timeline"} / {item.target_duration ? `${Number(item.target_duration).toFixed(1)}s` : "-"} / {item.aspect_ratio || "-"}
              </small>
              <em>{item.music_picture_score ? `music ${Number(item.music_picture_score).toFixed(1)}` : ""}</em>
            </a>
          ))}
        </div>
      ) : null}
    </section>
  );
}
