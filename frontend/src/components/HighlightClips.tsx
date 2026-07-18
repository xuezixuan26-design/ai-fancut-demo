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

export function HighlightClips({ clips }: { clips: Clip[] }) {
  return (
    <section className="widePanel">
      <div className="panelHeader">
        <h2>AI 识别出的高光片段</h2>
      </div>
      <div className="clipGrid">
        {clips.slice(0, 12).map((clip, index) => (
          <article className="clipCard" key={`${clip.source}-${clip.start}-${index}`}>
            <div className="clipTop">
              <strong>{clip.source}</strong>
              <span>{clip.highlight_score.toFixed(1)}</span>
            </div>
            <p>
              {clip.start}s - {clip.end}s / {clip.recommended_usage}
            </p>
            <div className="metrics">
              <span>清晰 {clip.sharpness_score.toFixed(1)}</span>
              <span>人脸 {(clip.face_ratio * 100).toFixed(1)}%</span>
              <span>构图 {clip.composition_score.toFixed(1)}</span>
              <span>氛围 {clip.atmosphere_score.toFixed(1)}</span>
            </div>
            <small>{clip.reason}</small>
          </article>
        ))}
      </div>
    </section>
  );
}
