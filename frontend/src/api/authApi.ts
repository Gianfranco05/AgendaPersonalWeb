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
    // Una sola casilla ("Tengo 16 años o más y acepto…") cubre las dos
    // declaraciones: el backend las pide por separado para poder auditarlas.
    confirm_age: acceptTerms,
  });
}

// Recuperación de contraseña y verificación de email. Los links de los mails
// del backend apuntan a /resetear-password y /verificar-email del SPA.
export async function forgotPassword(email: string): Promise<void> {
  await apiClient.post('/auth/api/forgot-password', { email });
}

export async function resetPassword(token: string, password: string): Promise<void> {
  await apiClient.post('/auth/api/reset-password', { token, password });
}

// Pide que se reenvíe el mail de verificación al usuario logueado.
export async function requestEmailVerification(): Promise<void> {
  await apiClient.post('/auth/api/verify-email/request');
}

export async function verifyEmail(token: string): Promise<void> {
  await apiClient.post('/auth/api/verify-email', { token });
}

export async function updateProfile(fullName: string): Promise<AuthUser> {
  const { data } = await apiClient.patch<AuthUser>('/auth/api/me', { full_name: fullName });
  return data;
}

export async function acceptTerms(version: string): Promise<AuthUser> {
  const { data } = await apiClient.post<AuthUser>('/auth/api/accept-terms', {
    version,
    confirm_age: true,
  });
  return data;
}
