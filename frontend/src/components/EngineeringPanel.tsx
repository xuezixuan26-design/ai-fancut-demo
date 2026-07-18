import { Clapperboard, Database, FileText, GitCompare, Images, RefreshCw, Send } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { getJson, postJson } from "../api/client";

const L = {
  title: "\u5de5\u7a0b\u5316\u8bc4\u4f30",
  visualTitle: "\u77e5\u8bc6\u5e93 / Harness \u53ef\u89c6\u5316",
  compress: "\u538b\u7f29\u4e0a\u4e0b\u6587",
  runHarness: "\u8dd1 Harness",
  renderPreview: "\u6e32\u67d3\u77ed\u6837\u7247",
  promote: "\u5e94\u7528\u63a8\u8350",
  promoteRender: "\u5e94\u7528\u5e76\u6e32\u67d3",
  kb: "\u77e5\u8bc6\u5e93",
  readReport: "\u8bfb\u53d6\u62a5\u544a",
  analyzeFrames: "\u5206\u6790\u62bd\u5e27",
  runCritic: "\u5ba1\u7247",
  reviseTimeline: "\u81ea\u52a8\u6539\u7a3f v2",
  framePlaceholder: "\u62bd\u5e27\u76ee\u5f55",
  feedbackPlaceholder:
    "\u53ef\u9009\uff1a\u8bb0\u5f55\u8fd9\u6b21\u4e0d\u6ee1\u610f\u6216\u504f\u597d\u7684\u53cd\u9988\uff0c\u4f8b\u5982\u6548\u679c\u91cd\u590d\u3001\u7247\u6bb5\u91cd\u590d\u3001\u97f3\u4e50\u5361\u70b9\u66f4\u514b\u5236\u3002",
  notCompressed: "\u5c1a\u672a\u538b\u7f29",
  recommended: "\u63a8\u8350",
  rendered: "\uff0c\u5df2\u6e32\u67d3\u77ed\u6837\u7247",
  notRun: "\u5c1a\u672a\u8fd0\u884c",
  promoted: "\u5df2\u5e94\u7528",
  timelineItems: "Timeline \u955c\u5934\u6570",
  renderStarted: "\u5df2\u5f00\u59cb\u6e32\u67d3",
  winner: "\u80dc\u51fa",
  next: "\u4e0b\u4e00\u6b65",
  preview: "\u9884\u89c8",
  human: "\u4eba\u5de5",
  musicScore: "\u97f3\u753b\u5206",
  strongBeat: "\u5f3a\u62cd",
  good: "\u597d",
  risk: "\u98ce\u9669",
  score6: "6\u5206",
  score8: "8\u5206",
  preferred: "\u4f18\u9009",
  notAnalyzed: "\u5c1a\u672a\u5206\u6790\u62bd\u5e27",
  notRead: "\u5c1a\u672a\u8bfb\u53d6",
  candidates: "\u5019\u9009\u7248\u672c",
  skillMap: "Skill \u5730\u56fe",
  frameLogic: "\u62bd\u5e27\u590d\u523b\u903b\u8f91",
  memory: "\u9879\u76ee\u8bb0\u5fc6",
  score: "\u5206\u6570",
  sourceDiversity: "\u7d20\u6750\u591a\u6837\u6027",
  centerCoverage: "\u4e3b\u4f53\u7a33\u5b9a",
  transitionSet: "\u8f6c\u573a\u7ec4",
  effectSet: "\u6548\u679c\u7ec4",
  openPreview: "\u6253\u5f00\u77ed\u6837\u7247",
  skills: "\u6761 skill",
  frameSkills: "\u6761 frame skill",
  memories: "\u6761\u8bb0\u5fc6",
};

type Props = { projectId?: string; busy?: boolean };

type HarnessExplanation = {
  why_good?: string[];
  why_risky?: string[];
  music_picture?: { score?: number; strong_beat_hit_rate?: number; drop_visual_change_avg?: number };
  selected_constraints?: Record<string, unknown>;
};

type HarnessRun = {
  run_id?: string;
  style_template: string;
  edit_profile?: string;
  score: number;
  preview_url?: string;
  explanation?: HarnessExplanation;
  human_feedback?: { human_score?: number };
  quality_report?: {
    music_picture_score?: number;
    warnings?: string[];
    timeline_source_diversity?: number;
    timeline_source_family_diversity?: number;
    crop_center_coverage?: number;
    top_source_share?: number;
    top_source_family_share?: number;
    source_usage?: Record<string, number>;
    source_family_usage?: Record<string, number>;
    effect_repeat_count?: number;
    transition_repeat_count?: number;
  };
  planner_constraints?: {
    opening_strategy?: string;
    cut_strategy?: string;
    motion_strategy?: string;
    shot_priority?: string[];
    preferred_style_template?: string;
  };
  effects?: string[];
  transitions?: string[];
  trajectory?: { step?: number; name?: string; action?: string; observation?: Record<string, unknown> }[];
  evidence?: {
    inputs?: { candidate_clip_count?: number; source_count?: number; aspect_ratio?: string };
    verification?: { warning_count?: number; slow_motion_violations?: unknown[]; strong_beat_hit_rate?: number };
    score_inputs?: { warning_count?: number; slow_motion_violation_count?: number };
  };
  version_manifest?: Record<string, unknown>;
};

type HarnessReport = {
  recommended_style?: string;
  rendered?: boolean;
  run_count?: number;
  target_duration?: number;
  input_fingerprint?: string;
  version_manifest?: Record<string, unknown>;
  comparison_summary?: {
    winner?: string;
    winner_score?: number;
    next_actions?: string[];
    main_differences?: { style_template?: string; score_delta?: number; winner_advantage?: string[] }[];
  };
  runs?: HarnessRun[];
};

type KbSkill = {
  skill_id?: string;
  skill_name?: string;
  type?: string;
  goal?: string;
};

type KbFrameSkill = {
  skill_name?: string;
  confidence?: number;
  frame_count?: number;
  ai_status?: string;
  structure_rules?: string[];
  frame_relation_rules?: string[];
  effect_mapping?: Record<string, string[]>;
  avoid_rules?: string[];
  detected_traits?: Record<string, unknown>;
};

type KbMemory = {
  style_fingerprint?: Record<string, unknown>;
  edit_summary?: {
    duration?: number;
    total_items?: number;
    top_roles?: [string, number][];
    top_effects?: [string, number][];
    top_transitions?: [string, number][];
  };
  asset_summary?: Record<string, unknown>;
  reuse_hints?: string[];
};

type KbSummary = {
  counts?: {
    skills?: number;
    template_profiles?: number;
    technical_catalogs?: number;
    frame_skills?: number;
    project_memories?: number;
  };
  skill_count?: number;
  frame_skill_count?: number;
  project_memory_count?: number;
  skills?: KbSkill[];
  technical_catalogs?: {
    skill_id?: string;
    skill_name?: string;
    goal?: string;
    camera_modes?: string[];
    transition_types?: string[];
    rules?: string[];
  }[];
  template_profiles?: {
    template_id?: string;
    template_name?: string;
    positioning?: string;
    camera?: { mode?: string; shot_duration_range?: number[]; strength?: number };
    transition?: { type?: string; duration_range?: number[]; strength?: number };
    render?: { filter?: string; strength?: number };
    material_fit?: string[];
  }[];
  reuse_hints?: [string, number][];
  latest_frame_skills?: KbFrameSkill[];
  latest_memories?: KbMemory[];
};

type FrameAnalysis = {
  learned_skill?: {
    name?: string;
    skill_name?: string;
    confidence?: number;
    frame_relation_rules?: string[];
    structure_rules?: string[];
    effect_mapping?: Record<string, string[]>;
  };
};

type PromoteResult = { promoted_style?: string; timeline_items?: number };
type RenderResult = { status?: string; progress?: number };
type CriticReport = {
  summary?: { issue_count?: number; high_count?: number; ready_for_final?: boolean; music_picture_score?: number };
  annotations?: { kind?: string; time_sec?: number; severity?: string; message?: string }[];
  proposed_actions?: { type?: string; reason?: string }[];
  reference_understanding?: {
    rhythm_curve?: { section?: string; energy?: number; cut_count?: number; flash_count?: number }[];
    shot_relation_rules?: string[];
  };
};
type RevisionResult = { revision_index?: number; change_count?: number; quality_report?: { music_picture_score?: number; warnings?: string[] } };

function fixText(value: unknown): string {
  if (value === null || value === undefined) return "";
  const text = String(value);
  if (!/[ÃÂÄÅÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖÙÚÛÜÝÞßà-ÿ\u0080-\u009f]/.test(text)) return text;
  try {
    const bytes = new Uint8Array([...text].map((char) => char.charCodeAt(0) & 255));
    const decoded = new TextDecoder("utf-8", { fatal: false }).decode(bytes);
    return decoded.replace(/\u0000/g, "") || text;
  } catch {
    return text;
  }
}

function fmt(value: unknown, digits = 1) {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(digits) : "-";
}

function pct(value: unknown) {
  return typeof value === "number" && Number.isFinite(value) ? `${Math.round(value * 100)}%` : "-";
}

function apiUrl(path?: string) {
  return path || "";
}

function chipList(items?: unknown[], limit = 5) {
  return (items || []).slice(0, limit).map((item) => fixText(item));
}

function shortName(value: string) {
  const text = fixText(value);
  if (text.length <= 22) return text;
  return `${text.slice(0, 8)}...${text.slice(-10)}`;
}

function frameSkillName(skill?: KbFrameSkill | FrameAnalysis["learned_skill"]) {
  if (!skill) return "";
  return fixText(("skill_name" in skill && skill.skill_name) || ("name" in skill && skill.name) || "");
}

export function EngineeringPanel({ projectId, busy }: Props) {
  const [feedback, setFeedback] = useState("");
  const [frameDir, setFrameDir] = useState("C:\\Users\\Lenovo\\Desktop\\jianji\\tutorial_analysis_frames");
  const [contextSummary, setContextSummary] = useState<Record<string, unknown> | null>(null);
  const [harnessReport, setHarnessReport] = useState<HarnessReport | null>(null);
  const [kbSummary, setKbSummary] = useState<KbSummary | null>(null);
  const [frameAnalysis, setFrameAnalysis] = useState<FrameAnalysis | null>(null);
  const [promoteResult, setPromoteResult] = useState<PromoteResult | null>(null);
  const [renderResult, setRenderResult] = useState<RenderResult | null>(null);
  const [criticReport, setCriticReport] = useState<CriticReport | null>(null);
  const [revisionResult, setRevisionResult] = useState<RevisionResult | null>(null);
  const [working, setWorking] = useState(false);
  const disabled = !projectId || busy || working;
  const skillCount = kbSummary?.skill_count ?? kbSummary?.counts?.skills ?? 0;
  const frameSkillCount = kbSummary?.frame_skill_count ?? kbSummary?.counts?.frame_skills ?? 0;
  const memoryCount = kbSummary?.project_memory_count ?? kbSummary?.counts?.project_memories ?? 0;

  const sortedRuns = useMemo(
    () => [...(harnessReport?.runs || [])].sort((a, b) => (b.score || 0) - (a.score || 0)),
    [harnessReport],
  );
  const winner = harnessReport?.comparison_summary?.winner || harnessReport?.recommended_style;
  const skillGroups = useMemo(() => {
    const groups = new Map<string, KbSkill[]>();
    (kbSummary?.skills || []).forEach((skill) => {
      const key = fixText(skill.type || "other");
      groups.set(key, [...(groups.get(key) || []), skill]);
    });
    return [...groups.entries()];
  }, [kbSummary]);
  const activeFrameSkill = frameAnalysis?.learned_skill || kbSummary?.latest_frame_skills?.[0];
  const latestMemory = kbSummary?.latest_memories?.[0];
  const technicalCatalog = kbSummary?.technical_catalogs?.[0];
  const templateProfiles = kbSummary?.template_profiles || [];

  useEffect(() => {
    if (!projectId) return;
    let cancelled = false;
    Promise.all([
      getJson(`/api/context/summary/${projectId}`).catch(() => null),
      getJson(`/api/harness/report/${projectId}`).catch(() => null),
      getJson("/api/kb/summary?compressed=true").catch(() => null),
    ]).then(([context, report, kb]) => {
      if (cancelled) return;
      setContextSummary(context as Record<string, unknown> | null);
      setHarnessReport(report as HarnessReport | null);
      setKbSummary(kb as KbSummary | null);
    });
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  async function runAction<T>(action: () => Promise<T>) {
    setWorking(true);
    try {
      return await action();
    } finally {
      setWorking(false);
    }
  }

  async function scoreRun(run: HarnessRun, humanScore: number, isWinner = false) {
    if (!projectId) return;
    await runAction(async () => {
      const scored = await postJson("/api/harness/score", {
        project_id: projectId,
        run_id: run.run_id || run.style_template,
        human_score: humanScore,
        winner: isWinner,
        liked: isWinner ? ["manual_winner"] : ["manual_score"],
      });
      const updatedReport = (scored as { updated_report?: HarnessReport }).updated_report;
      setHarnessReport(updatedReport || ((await getJson(`/api/harness/report/${projectId}`)) as HarnessReport));
    });
  }

  async function promoteWinner() {
    if (!projectId) return;
    await runAction(async () => {
      setPromoteResult(
        (await postJson("/api/harness/promote", {
          project_id: projectId,
          run_id: winner,
        })) as PromoteResult,
      );
    });
  }

  async function promoteAndRender() {
    if (!projectId) return;
    await runAction(async () => {
      const promoted = (await postJson("/api/harness/promote", {
        project_id: projectId,
        run_id: winner,
      })) as PromoteResult;
      setPromoteResult(promoted);
      setRenderResult(
        (await postJson("/api/render", {
          project_id: projectId,
          keep_original_audio: false,
          cleanup_sources: false,
        })) as RenderResult,
      );
    });
  }

  return (
    <section className="widePanel engineeringPanel">
      <div className="panelHeader">
        <h2>{L.title}</h2>
        <div className="panelActions">
          <button className="iconButton" disabled={disabled} onClick={() => runAction(async () => setContextSummary((await postJson("/api/context/compress", { project_id: projectId, feedback })) as Record<string, unknown>))}>
            <FileText size={16} />
            {L.compress}
          </button>
          <button className="iconButton" disabled={disabled} onClick={() => runAction(async () => setHarnessReport((await postJson("/api/harness/run", { project_id: projectId })) as HarnessReport))}>
            <GitCompare size={16} />
            {L.runHarness}
          </button>
          <button className="iconButton" disabled={disabled} onClick={() => runAction(async () => setHarnessReport((await postJson("/api/harness/preview-run", { project_id: projectId, target_duration: 12, render: true })) as HarnessReport))}>
            <Clapperboard size={16} />
            {L.renderPreview}
          </button>
          <button className="iconButton" disabled={disabled || !winner} onClick={promoteWinner}>
            <Send size={16} />
            {L.promote}
          </button>
          <button className="iconButton" disabled={disabled || !winner} onClick={promoteAndRender}>
            <Clapperboard size={16} />
            {L.promoteRender}
          </button>
          <button className="iconButton" disabled={disabled} onClick={() => runAction(async () => setCriticReport((await postJson("/api/critic/run", { project_id: projectId, apply_revision: false })) as CriticReport))}>
            <GitCompare size={16} />
            {L.runCritic}
          </button>
          <button className="iconButton" disabled={disabled} onClick={() => runAction(async () => setRevisionResult((await postJson("/api/critic/revise", { project_id: projectId, apply_revision: true })) as RevisionResult))}>
            <Send size={16} />
            {L.reviseTimeline}
          </button>
          <button className="iconButton" disabled={working} onClick={() => runAction(async () => setKbSummary((await getJson("/api/kb/summary?compressed=true")) as KbSummary))}>
            <Database size={16} />
            {L.kb}
          </button>
          <button
            className="iconButton"
            disabled={!projectId || working}
            onClick={() =>
              runAction(async () => {
                const [context, report, kb] = await Promise.all([
                  getJson(`/api/context/summary/${projectId}`).catch(() => null),
                  getJson(`/api/harness/report/${projectId}`).catch(() => null),
                  getJson("/api/kb/summary?compressed=true").catch(() => null),
                ]);
                setContextSummary(context as Record<string, unknown> | null);
                setHarnessReport(report as HarnessReport | null);
                setKbSummary(kb as KbSummary | null);
              })
            }
          >
            <RefreshCw size={16} />
            {L.readReport}
          </button>
        </div>
      </div>

      <div className="engineeringInputs">
        <textarea className="feedbackBox" value={feedback} placeholder={L.feedbackPlaceholder} onChange={(event) => setFeedback(event.target.value)} />
        <div className="frameAnalyzeRow">
          <input value={frameDir} onChange={(event) => setFrameDir(event.target.value)} placeholder={L.framePlaceholder} />
          <button className="iconButton" disabled={working} onClick={() => runAction(async () => setFrameAnalysis((await postJson("/api/frames/analyze", { project_id: projectId, frame_dir: frameDir, sample_limit: 12, use_ai: false })) as FrameAnalysis))}>
            <Images size={16} />
            {L.analyzeFrames}
          </button>
        </div>
      </div>

      <div className="visualWorkbench">
        <div className="visualHeader">
          <div>
            <h3>{L.visualTitle}</h3>
            <p>{winner ? `${L.winner}: ${fixText(winner)} / ${L.score}: ${fmt(harnessReport?.comparison_summary?.winner_score ?? sortedRuns[0]?.score, 2)}` : L.notRun}</p>
          </div>
          <div className="kpiStrip">
            <span><b>{harnessReport?.run_count || sortedRuns.length || 0}</b>{L.candidates}</span>
            <span><b>{skillCount}</b>{L.skills}</span>
            <span><b>{frameSkillCount}</b>{L.frameSkills}</span>
            <span><b>{memoryCount}</b>{L.memories}</span>
          </div>
        </div>

        {sortedRuns.length ? (
          <div className="candidateGrid">
            {sortedRuns.map((run, index) => {
              const isWinner = (run.run_id || run.style_template) === winner || run.style_template === winner;
              const music = run.explanation?.music_picture;
              return (
                <article className={`candidateCard${isWinner ? " winnerCard" : ""}`} key={run.run_id || run.style_template}>
                  <div className="candidateTop">
                    <div>
                      <strong>{index + 1}. {fixText(run.style_template)}</strong>
                      <small>{fixText(run.edit_profile || run.planner_constraints?.preferred_style_template || "")}</small>
                    </div>
                    <span>{fmt(run.score, 2)}</span>
                  </div>
                  {run.preview_url ? <video className="harnessVideo" src={apiUrl(run.preview_url)} controls preload="metadata" /> : null}
                  <div className="metricBars">
                    <label>
                      <span>{L.musicScore}</span>
                      <b>{fmt(music?.score ?? run.quality_report?.music_picture_score, 1)}</b>
                    </label>
                    <label>
                      <span>{L.strongBeat}</span>
                      <b>{pct(music?.strong_beat_hit_rate)}</b>
                    </label>
                    <label>
                      <span>Drop</span>
                      <b>{pct(music?.drop_visual_change_avg)}</b>
                    </label>
                    <label>
                      <span>{L.sourceDiversity}</span>
                      <b>{pct(run.quality_report?.timeline_source_diversity)}</b>
                    </label>
                    <label>
                      <span>源族覆盖</span>
                      <b>{pct(run.quality_report?.timeline_source_family_diversity)}</b>
                    </label>
                    <label>
                      <span>{L.centerCoverage}</span>
                      <b>{pct(run.quality_report?.crop_center_coverage)}</b>
                    </label>
                    <label>
                      <span>源族占比</span>
                      <b>{pct(run.quality_report?.top_source_family_share)}</b>
                    </label>
                  </div>
                  {run.preview_url ? <a className="previewLink" href={apiUrl(run.preview_url)} target="_blank" rel="noreferrer">{L.openPreview}</a> : null}
                  <div className="chipBlock">
                    <span>{L.effectSet}</span>
                    <div>{chipList(run.effects, 6).map((item) => <em key={item}>{item}</em>)}</div>
                  </div>
                  <div className="chipBlock">
                    <span>{L.transitionSet}</span>
                    <div>{chipList(run.transitions, 6).map((item) => <em key={item}>{item}</em>)}</div>
                  </div>
                  <div className="chipBlock">
                    <span>Harness Trace</span>
                    <div>
                      <em>{run.trajectory?.length || 0} steps</em>
                      <em>{fixText(run.version_manifest?.harness || "")}</em>
                      <em>{fixText(run.evidence?.inputs?.aspect_ratio || "")}</em>
                    </div>
                  </div>
                  <div className="chipBlock">
                    <span>Evidence</span>
                    <div>
                      <em>clips {run.evidence?.inputs?.candidate_clip_count ?? "-"}</em>
                      <em>sources {run.evidence?.inputs?.source_count ?? "-"}</em>
                      <em>slow violations {run.evidence?.score_inputs?.slow_motion_violation_count ?? 0}</em>
                    </div>
                  </div>
                  <div className="chipBlock">
                    <span>打分输入</span>
                    <div>
                      <em>warnings {run.evidence?.score_inputs?.warning_count ?? "-"}</em>
                      <em>top source {pct(run.quality_report?.top_source_share)}</em>
                      <em>top family {pct(run.quality_report?.top_source_family_share)}</em>
                      <em>effect repeats {run.quality_report?.effect_repeat_count ?? "-"}</em>
                      <em>transition repeats {run.quality_report?.transition_repeat_count ?? "-"}</em>
                    </div>
                  </div>
                  <div className="sourceFamilyBox">
                    <span>原视频族使用</span>
                    {Object.entries(run.quality_report?.source_family_usage || {}).length ? (
                      Object.entries(run.quality_report?.source_family_usage || {}).map(([name, count]) => (
                        <label key={name}>
                          <small title={fixText(name)}>{shortName(name)}</small>
                          <b>{count}</b>
                        </label>
                      ))
                    ) : (
                      <small>-</small>
                    )}
                  </div>
                  <div className="traceList">
                    <span>分析过程</span>
                    {(run.trajectory || []).slice(0, 6).map((step) => (
                      <p key={`${run.run_id}-${step.step}`}>
                        <b>{step.step}</b>
                        <small>{fixText(step.name)} / {fixText(step.action)}</small>
                      </p>
                    ))}
                  </div>
                  <div className="reasonList">
                    {run.explanation?.why_good?.slice(0, 2).map((item) => <p className="goodLine" key={item}>{fixText(item)}</p>)}
                    {run.explanation?.why_risky?.slice(0, 2).map((item) => <p className="riskLine" key={item}>{fixText(item)}</p>)}
                  </div>
                  <div className="scoreButtons">
                    <button disabled={working} onClick={() => scoreRun(run, 6)}>{L.score6}</button>
                    <button disabled={working} onClick={() => scoreRun(run, 8)}>{L.score8}</button>
                    <button disabled={working} onClick={() => scoreRun(run, 10, true)}>{L.preferred}</button>
                  </div>
                </article>
              );
            })}
          </div>
        ) : (
          <div className="emptyVisual">{L.notRun}</div>
        )}

        <div className="knowledgeVisualGrid">
          <article>
            <strong>{L.skillMap}</strong>
            {skillGroups.length ? (
              <div className="skillTypeGrid">
                {skillGroups.map(([type, skills]) => (
                  <div key={type}>
                    <b>{type}</b>
                    <small>{skills.length} skills</small>
                    {skills.slice(0, 4).map((skill) => (
                      <p key={skill.skill_id || skill.skill_name}>
                        <span>{fixText(skill.skill_name || skill.skill_id)}</span>
                        <small>{fixText(skill.goal)}</small>
                      </p>
                    ))}
                  </div>
                ))}
              </div>
            ) : (
              <small>{L.notRead}</small>
            )}
          </article>

          <article>
            <strong>{fixText(technicalCatalog?.skill_name || "\u6807\u51c6\u5316\u8fd0\u955c\u8f6c\u573a\u76ee\u5f55")}</strong>
            <small>{technicalCatalog ? fixText(technicalCatalog.goal) : L.notRead}</small>
            <div className="chipBlock">
              <span>\u8fd0\u955c\u6a21\u5f0f</span>
              <div>{(technicalCatalog?.camera_modes || []).slice(0, 10).map((item) => <em key={item}>{fixText(item)}</em>)}</div>
            </div>
            <div className="chipBlock">
              <span>\u8f6c\u573a\u7c7b\u578b</span>
              <div>{(technicalCatalog?.transition_types || []).slice(0, 10).map((item) => <em key={item}>{fixText(item)}</em>)}</div>
            </div>
            {technicalCatalog?.rules?.slice(0, 3).map((rule) => <p key={rule}>{fixText(rule)}</p>)}
          </article>

          <article>
            <strong>7\u7c7b\u7231\u8c46\u77ed\u89c6\u9891\u6a21\u677f</strong>
            {templateProfiles.length ? (
              <div className="templateProfileList">
                {templateProfiles.map((profile) => (
                  <div key={profile.template_id || profile.template_name}>
                    <b>{fixText(profile.template_name || profile.template_id)}</b>
                    <small>{fixText(profile.positioning)}</small>
                    <p>\u8fd0\u955c: {fixText(profile.camera?.mode)} / {profile.camera?.shot_duration_range?.join("-")}s / \u5f3a\u5ea6 {profile.camera?.strength}</p>
                    <p>\u8f6c\u573a: {fixText(profile.transition?.type)} / {profile.transition?.duration_range?.join("-")}s / \u5f3a\u5ea6 {profile.transition?.strength}</p>
                    <p>\u6e32\u67d3: {fixText(profile.render?.filter)} / \u5f3a\u5ea6 {profile.render?.strength}</p>
                    <div className="chipBlock">
                      <span>\u9002\u7528\u7d20\u6750</span>
                      <div>{(profile.material_fit || []).slice(0, 4).map((item) => <em key={item}>{fixText(item)}</em>)}</div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <small>{L.notRead}</small>
            )}
          </article>

          <article>
            <strong>{L.frameLogic}</strong>
            <small>
              {activeFrameSkill ? `${frameSkillName(activeFrameSkill)} / confidence ${fmt(activeFrameSkill.confidence, 2)}` : L.notAnalyzed}
            </small>
            {("structure_rules" in (activeFrameSkill || {}) ? activeFrameSkill?.structure_rules : undefined)?.slice(0, 4).map((rule) => <p key={rule}>{fixText(rule)}</p>)}
            {activeFrameSkill?.frame_relation_rules?.slice(0, 4).map((rule) => <p key={rule}>{fixText(rule)}</p>)}
            {"effect_mapping" in (activeFrameSkill || {}) && activeFrameSkill?.effect_mapping ? (
              <div className="chipBlock">
                <span>{L.effectSet}</span>
                <div>{Object.entries(activeFrameSkill.effect_mapping).flatMap(([key, list]) => [key, ...list]).slice(0, 10).map((item) => <em key={item}>{fixText(item)}</em>)}</div>
              </div>
            ) : null}
          </article>

          <article>
            <strong>{L.memory}</strong>
            {latestMemory ? (
              <>
                <div className="memoryStats">
                  <span>{fmt(latestMemory.edit_summary?.duration, 1)}s</span>
                  <span>{latestMemory.edit_summary?.total_items || 0} clips</span>
                  <span>{fixText(latestMemory.style_fingerprint?.edit_profile || "")}</span>
                </div>
                <div className="chipBlock">
                  <span>Top effects</span>
                  <div>{(latestMemory.edit_summary?.top_effects || []).slice(0, 5).map(([name]) => <em key={name}>{fixText(name)}</em>)}</div>
                </div>
                <div className="chipBlock">
                  <span>Reuse hints</span>
                  <div>{(latestMemory.reuse_hints || []).slice(0, 5).map((hint) => <em key={hint}>{fixText(hint)}</em>)}</div>
                </div>
              </>
            ) : (
              <small>{L.notRead}</small>
            )}
          </article>
        </div>
      </div>

      <div className="engineeringGrid">
        <article>
          <strong>Context Compression</strong>
          <small>{contextSummary ? `${String((contextSummary.edit_summary as { total_items?: number })?.total_items || 0)} timeline items` : L.notCompressed}</small>
          {contextSummary?.reuse_hints ? <p>{(contextSummary.reuse_hints as string[]).map(fixText).join(" / ")}</p> : null}
        </article>

        <article className="harnessCard">
          <strong>Harness</strong>
          <small>{harnessReport?.recommended_style ? `${L.recommended}: ${fixText(harnessReport.recommended_style)}${harnessReport.rendered ? L.rendered : ""}` : L.notRun}</small>
          {promoteResult ? (
            <div className="comparisonBox">
              <p>{L.promoted}: {fixText(promoteResult.promoted_style)}</p>
              <p>{L.timelineItems}: {promoteResult.timeline_items}</p>
              {renderResult ? <p>{L.renderStarted}: {renderResult.status} / {renderResult.progress}%</p> : null}
            </div>
          ) : null}
          {harnessReport?.comparison_summary ? (
            <div className="comparisonBox">
              <p>{L.winner}: {fixText(harnessReport.comparison_summary.winner)}</p>
              {harnessReport.comparison_summary.next_actions?.slice(0, 2).map((item) => <p key={item}>{L.next}: {fixText(item)}</p>)}
            </div>
          ) : null}
          {harnessReport?.runs?.slice(0, 4).map((run) => (
            <div className="harnessRunRow" key={run.run_id || run.style_template}>
              <p>
                {fixText(run.style_template)}: {run.score}
                {run.human_feedback?.human_score ? ` / ${L.human} ${run.human_feedback.human_score}` : ""}
                {run.preview_url ? <> <a href={apiUrl(run.preview_url)} target="_blank" rel="noreferrer">{L.preview}</a></> : null}
              </p>
              <small>
                {L.musicScore} {run.explanation?.music_picture?.score ?? run.quality_report?.music_picture_score ?? "-"} / {L.strongBeat} {run.explanation?.music_picture?.strong_beat_hit_rate ?? "-"} / drop {run.explanation?.music_picture?.drop_visual_change_avg ?? "-"}
              </small>
              {run.explanation?.why_good?.slice(0, 2).map((item) => <p key={item}>{L.good}: {fixText(item)}</p>)}
              {run.explanation?.why_risky?.slice(0, 2).map((item) => <p key={item}>{L.risk}: {fixText(item)}</p>)}
              <div className="scoreButtons">
                <button disabled={working} onClick={() => scoreRun(run, 6)}>{L.score6}</button>
                <button disabled={working} onClick={() => scoreRun(run, 8)}>{L.score8}</button>
                <button disabled={working} onClick={() => scoreRun(run, 10, true)}>{L.preferred}</button>
              </div>
            </div>
          ))}
        </article>

        <article>
          <strong>Frame-to-edit Skill</strong>
          <small>{frameAnalysis?.learned_skill ? `${fixText(frameAnalysis.learned_skill.name || frameAnalysis.learned_skill.skill_name)} / confidence ${frameAnalysis.learned_skill.confidence}` : L.notAnalyzed}</small>
          {frameAnalysis?.learned_skill?.frame_relation_rules?.slice(0, 2).map((rule) => <p key={rule}>{fixText(rule)}</p>)}
        </article>

        <article>
          <strong>Rendered Critic / Revision</strong>
          <small>
            {criticReport
              ? `issues ${criticReport.summary?.issue_count ?? 0} / high ${criticReport.summary?.high_count ?? 0} / ready ${criticReport.summary?.ready_for_final ? "yes" : "no"}`
              : "not reviewed"}
          </small>
          {criticReport?.annotations?.slice(0, 3).map((item, index) => (
            <p key={`${item.kind}-${index}`}>{fmt(item.time_sec, 1)}s {fixText(item.kind)}: {fixText(item.message)}</p>
          ))}
          {criticReport?.proposed_actions?.slice(0, 4).map((item) => <p key={item.type}>{fixText(item.type)} / {fixText(item.reason)}</p>)}
          {revisionResult ? (
            <div className="comparisonBox">
              <p>v{revisionResult.revision_index}: {revisionResult.change_count} changes</p>
              <p>music {fmt(revisionResult.quality_report?.music_picture_score, 1)}</p>
            </div>
          ) : null}
        </article>

        <article>
          <strong>Knowledge Base</strong>
          <small>{kbSummary ? `${skillCount} skills / ${frameSkillCount} frame skills / ${memoryCount} memories` : L.notRead}</small>
          {kbSummary?.reuse_hints?.slice(0, 4).map(([hint, count]) => <p key={hint}>{fixText(hint)}: {count}</p>)}
        </article>
      </div>
    </section>
  );
}
