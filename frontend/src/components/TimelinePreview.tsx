type Item = {
  source: string;
  start: number;
  end: number;
  speed: number;
  effect: string;
  transition: string;
  caption: string;
};

export function TimelinePreview({ timeline }: { timeline?: { timeline?: Item[]; title?: string; color_grade?: string } }) {
  const items = timeline?.timeline || [];
  return (
    <section className="widePanel">
      <div className="panelHeader">
        <h2>AI 生成的 Timeline</h2>
        {timeline?.color_grade && <span className="pill">{timeline.color_grade}</span>}
      </div>
      <div className="timeline">
        {items.map((item, index) => (
          <div className="timelineItem" key={`${item.source}-${index}`}>
            <b>{index + 1}</b>
            <span>{item.source}</span>
            <small>
              {item.start}s - {item.end}s · {item.speed}x · {item.effect} · {item.transition}
            </small>
            {item.caption && <em>{item.caption}</em>}
          </div>
        ))}
      </div>
    </section>
  );
}
