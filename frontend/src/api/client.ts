const API_BASE_STORAGE_KEY = "ai-fancut-api-base";

export function configuredApiBase() {
  if (typeof window === "undefined") return import.meta.env.VITE_API_BASE || "";
  return window.localStorage.getItem(API_BASE_STORAGE_KEY) || import.meta.env.VITE_API_BASE || "";
}

export function saveApiBase(value: string) {
  if (typeof window === "undefined") return;
  const normalized = value.trim().replace(/\/+$/, "");
  if (normalized) {
    window.localStorage.setItem(API_BASE_STORAGE_KEY, normalized);
  } else {
    window.localStorage.removeItem(API_BASE_STORAGE_KEY);
  }
}

export function defaultApiBase() {
  return import.meta.env.VITE_API_BASE || "";
}

export async function uploadFiles(path: string, files: File[], projectId?: string) {
  const form = new FormData();
  if (projectId) form.append("project_id", projectId);
  files.forEach((file) => form.append(path.includes("videos") ? "files" : "file", file));
  const res = await fetch(`${configuredApiBase()}${path}`, { method: "POST", body: form });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function postJson(path: string, body: unknown) {
  const res = await fetch(`${configuredApiBase()}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function getProject(projectId: string) {
  const res = await fetch(`${configuredApiBase()}/api/project/${projectId}`);
  if (!res.ok) throw new Error(await readError(res));
  return res.json();
}

export async function getJson(path: string) {
  const res = await fetch(`${configuredApiBase()}${path}`);
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
