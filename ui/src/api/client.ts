import { getApiBaseUrl } from "../config";
import type {
  ApiError,
  LoginResponse,
  Post,
  Role,
  User,
} from "./types";

export class ApiClientError extends Error {
  status: number;
  errorCode?: string;

  constructor(message: string, status: number, errorCode?: string) {
    super(message);
    this.status = status;
    this.errorCode = errorCode;
  }
}

async function parseError(response: Response): Promise<ApiClientError> {
  try {
    const body = (await response.json()) as ApiError;
    return new ApiClientError(
      body.message || response.statusText,
      response.status,
      body.errorCode,
    );
  } catch {
    return new ApiClientError(response.statusText || "Request failed", response.status);
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  token?: string | null,
): Promise<T> {
  const baseUrl = await getApiBaseUrl();
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${baseUrl}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  return request<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export async function listUsers(token: string): Promise<User[]> {
  const data = await request<{ items: User[] }>("/users", { method: "GET" }, token);
  return data.items;
}

export async function getUser(token: string, userId: string): Promise<User> {
  return request<User>(`/users/${userId}`, { method: "GET" }, token);
}

export async function updateUser(
  token: string,
  userId: string,
  body: { email?: string; name?: string },
): Promise<User> {
  return request<User>(
    `/users/${userId}`,
    { method: "PUT", body: JSON.stringify(body) },
    token,
  );
}

export async function deleteUser(token: string, userId: string): Promise<{ message: string }> {
  return request<{ message: string }>(`/users/${userId}`, { method: "DELETE" }, token);
}

export async function updateUserRole(
  token: string,
  userId: string,
  role: Role,
): Promise<User> {
  return request<User>(
    `/users/${userId}/role`,
    { method: "PUT", body: JSON.stringify({ role }) },
    token,
  );
}

export async function listPosts(token: string): Promise<Post[]> {
  const data = await request<{ items: Post[] }>("/posts", { method: "GET" }, token);
  return data.items;
}

export async function getPost(token: string, postId: string): Promise<Post> {
  return request<Post>(`/posts/${postId}`, { method: "GET" }, token);
}

export async function createPost(
  token: string,
  body: { title: string; body: string },
): Promise<Post> {
  return request<Post>("/posts", { method: "POST", body: JSON.stringify(body) }, token);
}

export async function updatePost(
  token: string,
  postId: string,
  body: { title?: string; body?: string },
): Promise<Post> {
  return request<Post>(
    `/posts/${postId}`,
    { method: "PUT", body: JSON.stringify(body) },
    token,
  );
}

export async function deletePost(token: string, postId: string): Promise<{ message: string }> {
  return request<{ message: string }>(`/posts/${postId}`, { method: "DELETE" }, token);
}

export function decodeJwtPayload(token: string): Record<string, unknown> {
  const parts = token.split(".");
  if (parts.length < 2) {
    return {};
  }
  const payload = parts[1].replace(/-/g, "+").replace(/_/g, "/");
  const json = atob(payload.padEnd(payload.length + ((4 - (payload.length % 4)) % 4), "="));
  return JSON.parse(json) as Record<string, unknown>;
}
