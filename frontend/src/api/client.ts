export const API_BASE = import.meta.env.VITE_API_BASE || "";

export async function uploadFiles(path: string, files: File[], projectId?: string) {
  const form = new FormData();
  if (projectId) form.append("project_id", projectId);
  files.forEach((file) => form.append(path.includes("videos") ? "files" : "file", file));
  const res = await fetch(`${API_BASE}${path}`, { method: "POST", body: form });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function postJson(path: string, body: unknown) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function getProject(projectId: string) {
  const res = await fetch(`${API_BASE}/api/project/${projectId}`);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function getJson(path: string) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

async function readError(res: Response) {
  try {
    const data = await res.json();
    return data.detail || res.statusText;
  } catch {
    return res.statusText;
  }
}
