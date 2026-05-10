import { HttpClient } from '@angular/common/http';
import { LoginResponse, RegistrationResponse, SessionResponse } from '../models/login-session.model';
import { DestroyRef, Injectable, computed, inject, signal } from '@angular/core';
import { Observable, tap } from 'rxjs';
import { Router } from '@angular/router';
import { environment } from '../../../environments/environment';
import { ChatOrchestrator } from './chat-orchestrator.service';

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private router = inject(Router);
  private httpClient = inject(HttpClient);
  private destroyRef = inject(DestroyRef);
  private chatOrchestrator = inject(ChatOrchestrator);

  private tokenSignal = signal<string | null>(localStorage.getItem('token'));
  private isAdminSignal = signal<boolean>(this.readAdminFromToken());
  isLoggedIn = computed(() => !!this.tokenSignal());
  token = computed(() => this.tokenSignal());
  isAdmin = computed(() => this.isAdminSignal());

  private decodeTokenPayload(token: string): Record<string, unknown> | null {
    try {
      const parts = token.split('.');
      if (parts.length !== 3) return null;
      let payload = parts[1].replace(/-/g, '+').replace(/_/g, '/');
      payload += '='.repeat((4 - (payload.length % 4)) % 4);
      return JSON.parse(atob(payload));
    } catch {
      return null;
    }
  }

  private readAdminFromToken(): boolean {
    const token = localStorage.getItem('token');
    if (!token) return false;
    const payload = this.decodeTokenPayload(token);
    return payload?.['is_admin'] === true;
  }

  private storeLoginTokens(token: string) {
    localStorage.setItem('token', token);
    localStorage.setItem('userToken', token);
    this.tokenSignal.set(token);
  }

  private storeSessionToken(token: string) {
    localStorage.setItem('token', token);
    this.tokenSignal.set(token);
    this.isAdminSignal.set(this.readAdminFromToken());
  }

  logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('userToken');
    this.tokenSignal.set(null);
    this.isAdminSignal.set(false);
    this.router.navigate(['/']);
  }

  /**
   * @description Login a user and create a session token
   * @param username - The username of the user
   * @param password - The password of the user
   * @returns An observable of the login response
   */
  login(username: string, password: string): Observable<LoginResponse> {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);
    formData.append('grant_type', 'password');
    return this.httpClient.post<LoginResponse>(`${environment.baseUrl}/api/v1/auth/login`, formData.toString(), {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    }).pipe(
      tap((response: LoginResponse) => {
        this.storeLoginTokens(response.access_token);
        const subscription = this.createSession().subscribe({
          error: (error) => {
            console.error(error);
          }
        });
        this.destroyRef.onDestroy(() => {
          subscription.unsubscribe();
        });
      })
    );

  }

  createSession(): Observable<SessionResponse> {
    return this.httpClient.post<SessionResponse>(`${environment.baseUrl}/api/v1/auth/session`, {}).pipe(
      tap((response: SessionResponse) => {
        this.storeSessionToken(response.token.access_token);
        this.chatOrchestrator.resetSession();
      })
    );
  }

  /**
   * @description Register a new user account (requires admin approval)
   * @param email - The email address for the new account
   * @param password - The password for the new account
   * @returns An observable of the registration response
   */
  register(email: string, password: string): Observable<RegistrationResponse> {
    return this.httpClient.post<RegistrationResponse>(
      `${environment.baseUrl}/api/v1/auth/register`,
      { email, password }
    );
  }
}
