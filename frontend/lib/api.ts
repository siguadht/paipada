export type DesignStatus =
  | "pending"
  | "understanding"
  | "rendering_front"
  | "front_ready"
  | "editing"
  | "rendering_iso"
  | "completed"
  | "failed";

export type Version = {
  number: number;
  image_url: string;
  operation: string;
  instruction: string;
};

export type Product = {
  id: string;
  name: string;
  category: string;
  brand: string;
  price: number | null;
  style: string;
  color: string;
  image_url?: string;
  source_url?: string;
  demo_only?: boolean;
};

export type DesignHotspot = {
  id: string;
  product_id: string;
  x: number;
  y: number;
};

export type DesignLayerSet = {
  status: "queued" | "processing" | "ready" | "failed";
  base_image_url: string;
  layers: { name: string; description: string; image_url: string; box: [number, number, number, number]; z_index: number }[];
  error_message: string;
};

export type Design = {
  design_id: string;
  status: DesignStatus;
  current_step: string;
  photo_url: string;
  references: { style?: string; furniture?: string };
  reference_ids: { style?: string; furniture?: string };
  front_image_url: string;
  iso_image_url: string;
  current_version: number;
  is_concept_view: boolean;
  versions: Version[];
  hotspots: DesignHotspot[];
  layer_set: DesignLayerSet | null;
  user_input: string;
  design_notes: string[];
  edit_history: { version: number; operation: string; detail: string }[];
  error: { code: string; message: string } | null;
  is_mock: boolean;
  created_at: string;
};

export type HomeProject = {
  id: string;
  name: string;
  style_text: string;
  style_photo_id: string | null;
  style_photo_url: string;
  created_at: string;
  spaces: { id: string; name: string; style_snapshot: string; design: Design }[];
};

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000/api/v1";
const TOKEN_KEY = "paipaida-token";

export class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
  }
}

export function getToken(): string {
  return typeof window === "undefined" ? "" : sessionStorage.getItem(TOKEN_KEY) || "";
}

export function setToken(token: string) {
  sessionStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  sessionStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, { ...init, headers, cache: "no-store" });
  } catch {
    throw new ApiError("网络暂时不可用，请检查后端是否启动", 0);
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    if (response.status === 401) clearToken();
    throw new ApiError(body?.error?.message || "请求失败，请稍后重试", response.status);
  }
  return response.json() as Promise<T>;
}

export const api = {
  login: (inviteCode: string) =>
    request<{ token: string; user_id: number }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ invite_code: inviteCode.trim() }),
    }),
  me: () => request<{ user_id: number }>("/auth/me"),
  upload: (file: File) => {
    const body = new FormData();
    body.append("file", file);
    return request<{ photo_id: string; url: string }>("/uploads", { method: "POST", body });
  },
  createDesign: (photoId: string, userInput: string, references?: { style_photo_id?: string; furniture_photo_id?: string; home_id?: string; room_name?: string; cost_confirmed?: boolean }) =>
    request<Design>("/designs", {
      method: "POST",
      body: JSON.stringify({ photo_id: photoId, user_input: userInput, ...references }),
    }),
  updateReferences: (id: string, references: { style_photo_id?: string; furniture_photo_id?: string }) =>
    request<Design>(`/designs/${id}/references`, { method: "PUT", body: JSON.stringify(references) }),
  getDesign: (id: string) => request<Design>(`/designs/${id}`),
  prepareLayers: (id: string, costConfirmed: boolean) =>
    request<Design>(`/designs/${id}/layers`, { method: "POST", body: JSON.stringify({ cost_confirmed: costConfirmed }) }),
  listDesigns: () => request<{ designs: Design[] }>("/designs"),
  listHomes: () => request<{ homes: HomeProject[] }>("/homes"),
  getHome: (id: string) => request<HomeProject>(`/homes/${id}`),
  createHome: (payload: { name: string; style_text: string; style_photo_id?: string }) =>
    request<HomeProject>("/homes", { method: "POST", body: JSON.stringify(payload) }),
  updateHome: (id: string, payload: { name: string; style_text: string; style_photo_id?: string | null }) =>
    request<HomeProject>(`/homes/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  useSpaceAsStyle: (homeId: string, spaceId: string) =>
    request<HomeProject>(`/homes/${homeId}/style-from-space/${spaceId}`, { method: "POST" }),
  listProducts: () => request<{ products: Product[] }>("/designs/products"),
  addHotspot: (id: string, payload: { product_id: string; x: number; y: number }) =>
    request<Design & { added_hotspot_id: string }>(`/designs/${id}/hotspots`, { method: "POST", body: JSON.stringify(payload) }),
  deleteHotspot: (id: string, hotspotId: string) =>
    request<Design>(`/designs/${id}/hotspots/${hotspotId}`, { method: "DELETE" }),
  edit: (id: string, payload: { operation: "delete" | "replace" | "recolor" | "style" | "restore_structure"; x?: number; y?: number; detail: string; layer_index?: number; product_id?: string }) =>
    request<Design>(`/designs/${id}/edits`, { method: "POST", body: JSON.stringify(payload) }),
  regenerate: (id: string, feedback: string, viewMode: "original" | "concept" = "original") =>
    request<Design>(`/designs/${id}/regenerate`, { method: "POST", body: JSON.stringify({ feedback, view_mode: viewMode }) }),
  restore: (id: string, number: number) =>
    request<Design>(`/designs/${id}/versions/${number}/restore`, { method: "POST" }),
  confirm: (id: string, review?: { mode: "original" | "concept"; doors_windows?: boolean; walls_floor?: boolean; camera_layout?: boolean; concept_acknowledged?: boolean }) =>
    request<Design>(`/designs/${id}/confirm`, { method: "POST", ...(review ? { body: JSON.stringify({ review }) } : {}) }),
};

export async function fetchProtectedImage(path: string, signal: AbortSignal): Promise<string> {
  if (!path) return "";
  const headers = new Headers();
  headers.set("Authorization", `Bearer ${getToken()}`);
  const response = await fetch(`${BASE.replace(/\/api\/v1$/, "")}${path}`, { headers, signal, cache: "no-store" });
  if (!response.ok) throw new ApiError("图片暂时无法加载", response.status);
  return URL.createObjectURL(await response.blob());
}
