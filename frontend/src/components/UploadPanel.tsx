import { useState } from "react";
import { UploadCloud, X } from "lucide-react";

type Props = {
  title: string;
  accept: string;
  multiple?: boolean;
  files: File[];
  onChange: (files: File[]) => void;
};

export function UploadPanel({ title, accept, multiple, files, onChange }: Props) {
  const [dragging, setDragging] = useState(false);

  function handleFiles(nextFiles: FileList | null) {
    const selected = Array.from(nextFiles || []).filter((file) => isAccepted(file, accept));
    if (!multiple) {
      onChange(selected.slice(0, 1));
      return;
    }

    const merged = [...files, ...selected];
    const unique = merged.filter(
      (file, index, all) =>
        all.findIndex((item) => item.name === file.name && item.size === file.size && item.lastModified === file.lastModified) === index
    );
    onChange(unique);
  }

  function removeFile(fileToRemove: File) {
    onChange(files.filter((file) => file !== fileToRemove));
  }

  return (
    <section className="panel">
      <div className="panelHeader">
        <UploadCloud size={18} />
        <h2>{title}</h2>
      </div>
      <label
        className={`dropzone${dragging ? " dragging" : ""}`}
        onDragEnter={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={(event) => {
          event.preventDefault();
          setDragging(false);
        }}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          handleFiles(event.dataTransfer.files);
        }}
      >
        <input
          type="file"
          accept={accept}
          multiple={multiple}
          onChange={(event) => {
            handleFiles(event.target.files);
            event.currentTarget.value = "";
          }}
        />
        <span>{multiple ? "拖拽或选择多段素材" : "拖拽或选择文件"}</span>
      </label>
      <div className="fileList">
        {files.length === 0 ? (
          <p>未选择文件</p>
        ) : (
          files.map((file) => (
            <div className="fileItem" key={`${file.name}-${file.size}-${file.lastModified}`}>
              <p>{file.name}</p>
              <button type="button" className="removeFile" aria-label={`移除 ${file.name}`} onClick={() => removeFile(file)}>
                <X size={14} />
              </button>
            </div>
          ))
        )}
      </div>
    </section>
  );
}

function isAccepted(file: File, accept: string) {
  const suffix = `.${file.name.split(".").pop()?.toLowerCase()}`;
  return accept
    .split(",")
    .map((item) => item.trim().toLowerCase())
    .includes(suffix);
}
