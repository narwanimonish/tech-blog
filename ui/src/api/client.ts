import { getApiBaseUrl } from "../config";
import type {
  ApiError,
  ListOptions,
  LoginResponse,
  PaginatedList,
  Post,
  Role,
  User,
} from "./types";

export const API_UNAVAILABLE_MESSAGE =
  "API unavailable — the backend may be down or a deployment is in progress. Try again shortly or check your CDK/CloudFormation deploy status.";

export class ApiClientError extends Error {
  status: number;
  errorCode?: string;

  constructor(message: string, status: number, errorCode?: string) {
    super(message);
    this.status = status;
    this.errorCode = errorCode;
  }
}

/** Thrown when fetch fails (network error, CORS block, connection reset). */
export class ApiNetworkError extends Error {
  readonly isNetworkError = true;

  constructor(message = "Network request failed") {
    super(message);
  }
}

export function isApiUnavailableError(err: unknown): boolean {
  if (err instanceof ApiNetworkError) {
    return true;
  }
  if (err instanceof TypeError) {
    return true;
  }
  if (err instanceof ApiClientError) {
    return err.status === 0 || err.status === 502 || err.status === 503 || err.status === 504;
  }
  return false;
}

export function formatApiError(err: unknown, fallback: string): string {
  if (isApiUnavailableError(err)) {
    return API_UNAVAILABLE_MESSAGE;
  }
  if (err instanceof ApiClientError) {
    return err.message || fallback;
  }
  return fallback;
}

async function parseError(response: Response): Promise<ApiClientError> {
  if (response.status === 502 || response.status === 503 || response.status === 504) {
    return new ApiClientError(API_UNAVAILABLE_MESSAGE, response.status);
  }

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

  let response: Response;
  try {
    response = await fetch(`${baseUrl}${path}`, {
      ...options,
      headers,
    });
  } catch (err) {
    throw new ApiNetworkError(err instanceof Error ? err.message : "Network request failed");
  }

  if (!response.ok) {
    throw await parseError(response);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  try {
    return (await response.json()) as T;
  } catch {
    throw new ApiClientError(API_UNAVAILABLE_MESSAGE, response.status || 502);
  }
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  return request<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

function listQuery(options: ListOptions = {}): string {
  const params = new URLSearchParams();
  if (options.nextToken) {
    params.set("nextToken", options.nextToken);
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}

export async function listUsers(
  token: string,
  options: ListOptions = {},
): Promise<PaginatedList<User>> {
  return request<PaginatedList<User>>(`/users${listQuery(options)}`, { method: "GET" }, token);
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

export async function listPosts(
  token: string,
  options: ListOptions = {},
): Promise<PaginatedList<Post>> {
  return request<PaginatedList<Post>>(`/posts${listQuery(options)}`, { method: "GET" }, token);
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
