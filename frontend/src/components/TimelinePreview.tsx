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
  applied_skills?: AppliedSkill[];
  tracks?: Track[];
};

export function TimelinePreview({ timeline }: { timeline?: Timeline }) {
  const items = timeline?.timeline || [];
  const skills = timeline?.applied_skills || [];
  const tracks = timeline?.tracks || [];
  return (
    <section className="widePanel">
      <div className="panelHeader">
        <h2>AI 生成的 Timeline</h2>
        {timeline?.color_grade && <span className="pill">{timeline.color_grade}</span>}
      </div>
      {skills.length > 0 && (
        <div className="skillGrid">
          {skills.map((skill) => (
            <article className="skillCard" key={skill.skill_id}>
              <strong>{skill.skill_name}</strong>
              <span>{skill.type} · {(skill.confidence * 100).toFixed(0)}%</span>
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
              {item.start}s - {item.end}s · {item.speed}x · {item.effect} · {item.transition}
            </small>
            <small>
              {item.role || "beat_cut"} · {item.shot_size || "unknown"} · {item.subject_position || "unknown"}
            </small>
            {item.caption && <em>{item.caption}</em>}
          </div>
        ))}
      </div>
    </section>
  );
}
