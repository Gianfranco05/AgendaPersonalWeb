import apiClient from './client';
import type { AuthUser } from '../types/auth';

export async function login(email: string, password: string): Promise<AuthUser> {
  const { data } = await apiClient.post<AuthUser>('/auth/api/login', { email, password });
  return data;
}

export async function logout(): Promise<void> {
  await apiClient.post('/auth/api/logout');
}

export async function getMe(): Promise<AuthUser> {
  const { data } = await apiClient.get<AuthUser>('/auth/api/me');
  return data;
}

export async function register(
  name: string,
  email: string,
  password: string,
  acceptTerms: boolean,
): Promise<void> {
  await apiClient.post('/auth/api/register', {
    full_name: name,
    email,
    password,
    accept_terms: acceptTerms,
  });
}

export async function updateProfile(fullName: string): Promise<AuthUser> {
  const { data } = await apiClient.patch<AuthUser>('/auth/api/me', { full_name: fullName });
  return data;
}

export async function acceptTerms(version: string): Promise<AuthUser> {
  const { data } = await apiClient.post<AuthUser>('/auth/api/accept-terms', { version });
  return data;
}
