import { Download } from "lucide-react";

export function VideoPreview({ projectId }: { projectId?: string }) {
  if (!projectId) return null;
  const url = `/api/output/${projectId}`;
  return (
    <section className="previewPanel">
      <div className="panelHeader">
        <h2>成片预览</h2>
        <a className="iconButton" href={url} download>
          <Download size={16} />
          下载
        </a>
      </div>
      <video className="videoPreview" src={url} controls />
    </section>
  );
}
