import { UploadCloud } from "lucide-react";

type Props = {
  title: string;
  accept: string;
  multiple?: boolean;
  files: File[];
  onChange: (files: File[]) => void;
};

export function UploadPanel({ title, accept, multiple, files, onChange }: Props) {
  return (
    <section className="panel">
      <div className="panelHeader">
        <UploadCloud size={18} />
        <h2>{title}</h2>
      </div>
      <label className="dropzone">
        <input
          type="file"
          accept={accept}
          multiple={multiple}
          onChange={(event) => onChange(Array.from(event.target.files || []))}
        />
        <span>{multiple ? "选择多段素材" : "选择文件"}</span>
      </label>
      <div className="fileList">
        {files.length === 0 ? <p>未选择文件</p> : files.map((file) => <p key={file.name}>{file.name}</p>)}
      </div>
    </section>
  );
}
