import { ApplicationConfig, inject, provideBrowserGlobalErrorListeners, provideZonelessChangeDetection } from '@angular/core';
import { provideRouter } from '@angular/router';

import { routes } from './app.routes';
import { HttpErrorResponse, HttpEvent, HttpHandlerFn, HttpRequest, provideHttpClient, withInterceptors } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { AuthService } from './core/services/auth.service';

function bearerTokenInterceptor(request: HttpRequest<any>, next: HttpHandlerFn): Observable<HttpEvent<any>> {
  const isSessionCreation = request.url.includes('/api/v1/auth/session') && request.method === 'POST';
  const token = isSessionCreation
    ? (localStorage.getItem('userToken') ?? localStorage.getItem('token'))
    : localStorage.getItem('token');
  
  if (token) {
    request = request.clone({
      setHeaders: { Authorization: `Bearer ${token}` }
    });
  }
  return next(request);
}

function unauthorizedInterceptor(request: HttpRequest<any>, next: HttpHandlerFn): Observable<HttpEvent<any>> {
  const authService = inject(AuthService);
  const isLoginRequest = request.url.includes('/api/v1/auth/login');

  return next(request).pipe(
    tap({
      error: (event) => {
        if (event instanceof HttpErrorResponse && event.status === 401 && !isLoginRequest) {
          authService.logout();
        }
      },
    })
  );
}

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideZonelessChangeDetection(),
    provideRouter(routes),
    provideHttpClient(withInterceptors([bearerTokenInterceptor, unauthorizedInterceptor]))
  ]
};
