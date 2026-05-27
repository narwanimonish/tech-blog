export type Role = "admin" | "writer" | "reader";

export interface User {
  userId: string;
  email: string;
  name?: string;
  role: Role;
}

export interface Post {
  postId: string;
  title: string;
  body: string;
  creation_time: string;
  created_by: string;
}

export interface LoginResponse {
  accessToken: string;
  idToken: string;
  refreshToken?: string;
  expiresIn?: number;
  tokenType?: string;
}

export interface ApiError {
  errorCode?: string;
  message: string;
}

export interface AppConfig {
  apiUrl: string;
}
