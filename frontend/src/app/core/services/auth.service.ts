import { HttpClient } from '@angular/common/http';
import { LoginResponse } from '../models/login-session.model';
import { DestroyRef, Injectable, computed, inject, signal } from '@angular/core';
import { Observable, tap } from 'rxjs';
import { SessionResponse } from '../models/login-session.model';
import { Router } from '@angular/router';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private router = inject(Router);
  private httpClient = inject(HttpClient);
  private destroyRef = inject(DestroyRef);

  private tokenSignal = signal<string | null>(localStorage.getItem('token'));
  isLoggedIn = computed(() => !!this.tokenSignal());
  token = computed(() => this.tokenSignal() );


  private storeLoginTokens(token: string) {
    // Have to store token in two places because we will use the login token 
    // to immediately create a session token and the session token will be used 
    // to authenticate the user for the rest of the session
    // We need to overwrite token because we will use an http interceptor 
    // to add the token to the request header
    localStorage.setItem('token', token);
    localStorage.setItem('userToken', token);
    this.tokenSignal.set(token);
  }

  private storeSessionToken(token: string) {
    localStorage.setItem('token', token);
    this.tokenSignal.set(token);
  }

  logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('userToken');
    this.tokenSignal.set(null);
    this.router.navigate(['/']);
    // TODO: set graph state messages to 0
  }

  /**
   * @description Login a user and create a session token
   * @param username - The username of the user
   * @param password - The password of the user
   * @returns An observable of the login response
   */
  login(username: string, password: string): Observable<LoginResponse> {
    const formData = new FormData();
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
        // TODO: reset graph state messages
      })
    );
  }
}
