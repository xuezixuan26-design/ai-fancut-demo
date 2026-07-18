type Item = {
  source: string;
  start: number;
  end: number;
  speed: number;
  effect: string;
  transition: string;
  caption: string;
  role?: string;
  shot_size?: string;
  subject_position?: string;
};

type AppliedSkill = {
  skill_id: string;
  skill_name: string;
  type: string;
  confidence: number;
  reason: string;
};

type Track = {
  track_id: string;
  track_type: string;
  label: string;
  items?: {
    kind: string;
    start: number;
    end: number;
    source?: string;
    effect?: string;
  }[];
};

type Timeline = {
  timeline?: Item[];
  title?: string;
  color_grade?: string;
  style_fingerprint?: Record<string, string | number | boolean | null>;
  edit_decisions?: {
    hook_source?: string;
    hero_sources?: string[];
    motion_strategy?: string;
    effect_strategy?: string;
    caption_strategy?: string;
    climax_strategy?: string;
    music_strategy?: string;
  };
  applied_skills?: AppliedSkill[];
  tracks?: Track[];
  quality_report?: {
    total_items: number;
    unique_sources: number;
    available_sources: number;
    timeline_source_diversity: number;
    crop_center_coverage: number;
    consecutive_repeat_count: number;
    warnings?: string[];
  };
};

export function TimelinePreview({ timeline }: { timeline?: Timeline }) {
  const items = timeline?.timeline || [];
  const skills = timeline?.applied_skills || [];
  const tracks = timeline?.tracks || [];
  const quality = timeline?.quality_report;
  const fingerprint = timeline?.style_fingerprint;
  const decisions = timeline?.edit_decisions;
  return (
    <section className="widePanel">
      <div className="panelHeader">
        <h2>AI 生成的 Timeline</h2>
        {timeline?.color_grade && <span className="pill">{timeline.color_grade}</span>}
      </div>
      {quality && (
        <div className="qualityGrid">
          <div>
            <strong>{quality.total_items}</strong>
            <span>片段数</span>
          </div>
          <div>
            <strong>
              {quality.unique_sources}/{quality.available_sources}
            </strong>
            <span>素材覆盖</span>
          </div>
          <div>
            <strong>{(quality.timeline_source_diversity * 100).toFixed(0)}%</strong>
            <span>多素材轮换</span>
          </div>
          <div>
            <strong>{(quality.crop_center_coverage * 100).toFixed(0)}%</strong>
            <span>裁切中心</span>
          </div>
          <div>
            <strong>{quality.consecutive_repeat_count}</strong>
            <span>连续重复</span>
          </div>
        </div>
      )}
      {quality?.warnings?.length ? (
        <div className="warningList">
          {quality.warnings.map((warning) => (
            <p key={warning}>{warning}</p>
          ))}
        </div>
      ) : null}
      {(fingerprint || decisions) && (
        <div className="decisionGrid">
          {decisions?.hook_source && (
            <div>
              <span>Hook 镜头</span>
              <strong>{decisions.hook_source}</strong>
            </div>
          )}
          {decisions?.motion_strategy && (
            <div>
              <span>运镜策略</span>
              <strong>{decisions.motion_strategy}</strong>
            </div>
          )}
          {decisions?.effect_strategy && (
            <div>
              <span>效果强度</span>
              <strong>{decisions.effect_strategy}</strong>
            </div>
          )}
          {decisions?.climax_strategy && (
            <div>
              <span>高潮策略</span>
              <strong>{decisions.climax_strategy}</strong>
            </div>
          )}
          {decisions?.music_strategy && (
            <div>
              <span>音乐处理</span>
              <strong>{decisions.music_strategy}</strong>
            </div>
          )}
          {fingerprint?.opening_pattern && (
            <div>
              <span>开头模式</span>
              <strong>{fingerprint.opening_pattern}</strong>
            </div>
          )}
          {fingerprint?.cut_density && (
            <div>
              <span>剪辑密度</span>
              <strong>{fingerprint.cut_density}</strong>
            </div>
          )}
        </div>
      )}
      {skills.length > 0 && (
        <div className="skillGrid">
          {skills.map((skill) => (
            <article className="skillCard" key={skill.skill_id}>
              <strong>{skill.skill_name}</strong>
              <span>
                {skill.type} / {(skill.confidence * 100).toFixed(0)}%
              </span>
              <small>{skill.reason}</small>
            </article>
          ))}
        </div>
      )}
      {tracks.length > 0 && (
        <div className="trackList">
          {tracks.map((track) => (
            <div className="trackRow" key={track.track_id}>
              <b>{track.label}</b>
              <span>{track.track_type}</span>
              <small>{track.items?.length || 0} items</small>
            </div>
          ))}
        </div>
      )}
      <div className="timeline">
        {items.map((item, index) => (
          <div className="timelineItem" key={`${item.source}-${index}`}>
            <b>{index + 1}</b>
            <span>{item.source}</span>
            <small>
              {item.start}s - {item.end}s / {item.speed}x / {item.effect} / {item.transition}
            </small>
            <small>
              {item.role || "beat_cut"} / {item.shot_size || "unknown"} / {item.subject_position || "unknown"}
            </small>
            {item.caption && <em>{item.caption}</em>}
          </div>
        ))}
      </div>
    </section>
  );
}
