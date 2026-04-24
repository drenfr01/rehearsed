import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { Router } from '@angular/router';
import { AuthService } from './auth.service';
import { environment } from '../../../environments/environment';

/** Build a minimal JWT with the given payload (no real signature). */
function fakeJwt(payload: Record<string, unknown>): string {
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
  const body = btoa(JSON.stringify(payload));
  return `${header}.${body}.fake-signature`;
}

describe('AuthService', () => {
  let service: AuthService;
  let httpTesting: HttpTestingController;
  let router: Router;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
      ],
    });
    service = TestBed.inject(AuthService);
    httpTesting = TestBed.inject(HttpTestingController);
    router = TestBed.inject(Router);
  });

  afterEach(() => {
    httpTesting.verify();
    localStorage.clear();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should start as not logged in when no token in localStorage', () => {
    expect(service.isLoggedIn()).toBeFalse();
    expect(service.token()).toBeNull();
    expect(service.isAdmin()).toBeFalse();
  });

  describe('login', () => {
    it('should POST form data to login endpoint', () => {
      service.login('user@test.com', 'pass123').subscribe();

      const req = httpTesting.expectOne(`${environment.baseUrl}/api/v1/auth/login`);
      expect(req.request.method).toBe('POST');
      expect(req.request.headers.get('Content-Type')).toBe('application/x-www-form-urlencoded');

      req.flush({
        access_token: 'test-token',
        token_type: 'bearer',
        expires_at: '2026-12-31',
        is_admin: false,
      });

      const sessionToken = fakeJwt({ sub: 'sess-1', type: 'session', is_admin: false });
      const sessionReq = httpTesting.expectOne(`${environment.baseUrl}/api/v1/auth/session`);
      sessionReq.flush({
        session_id: 's1',
        name: 'session',
        token: { access_token: sessionToken, token_type: 'bearer', expires_at: '2026-12-31' },
      });

      expect(service.isLoggedIn()).toBeTrue();
    });

    it('should derive admin status from session token JWT, not localStorage flag', () => {
      service.login('admin@test.com', 'pass').subscribe();

      httpTesting.expectOne(`${environment.baseUrl}/api/v1/auth/login`).flush({
        access_token: 'admin-user-token',
        token_type: 'bearer',
        expires_at: '2026-12-31',
        is_admin: true,
      });

      const sessionToken = fakeJwt({ sub: 'sess-1', type: 'session', is_admin: true });
      httpTesting.expectOne(`${environment.baseUrl}/api/v1/auth/session`).flush({
        session_id: 's1',
        name: 'session',
        token: { access_token: sessionToken, token_type: 'bearer', expires_at: '2026-12-31' },
      });

      expect(service.isAdmin()).toBeTrue();
      // isAdmin is no longer stored in localStorage
      expect(localStorage.getItem('isAdmin')).toBeNull();
    });

    it('should set isAdmin false when session token has no is_admin claim', () => {
      service.login('user@test.com', 'pass').subscribe();

      httpTesting.expectOne(`${environment.baseUrl}/api/v1/auth/login`).flush({
        access_token: 'user-token',
        token_type: 'bearer',
        expires_at: '2026-12-31',
        is_admin: false,
      });

      const sessionToken = fakeJwt({ sub: 'sess-1', type: 'session', is_admin: false });
      httpTesting.expectOne(`${environment.baseUrl}/api/v1/auth/session`).flush({
        session_id: 's1',
        name: 'session',
        token: { access_token: sessionToken, token_type: 'bearer', expires_at: '2026-12-31' },
      });

      expect(service.isAdmin()).toBeFalse();
    });
  });

  describe('logout', () => {
    it('should clear tokens and navigate to root', () => {
      spyOn(router, 'navigate');
      localStorage.setItem('token', 'some-token');
      localStorage.setItem('userToken', 'some-token');

      service.logout();

      expect(localStorage.getItem('token')).toBeNull();
      expect(localStorage.getItem('userToken')).toBeNull();
      expect(service.isLoggedIn()).toBeFalse();
      expect(service.isAdmin()).toBeFalse();
      expect(router.navigate).toHaveBeenCalledWith(['/']);
    });
  });

  describe('createSession', () => {
    it('should POST to session endpoint and store session token', () => {
      const sessionToken = fakeJwt({ sub: 'sess-1', type: 'session', is_admin: false });
      service.createSession().subscribe();

      const req = httpTesting.expectOne(`${environment.baseUrl}/api/v1/auth/session`);
      expect(req.request.method).toBe('POST');
      req.flush({
        session_id: 's1',
        name: 'test',
        token: { access_token: sessionToken, token_type: 'bearer', expires_at: '2026-12-31' },
      });

      expect(localStorage.getItem('token')).toBe(sessionToken);
      expect(service.token()).toBe(sessionToken);
    });

    it('should update isAdmin signal from new session token', () => {
      const adminSessionToken = fakeJwt({ sub: 'sess-2', type: 'session', is_admin: true });
      service.createSession().subscribe();

      httpTesting.expectOne(`${environment.baseUrl}/api/v1/auth/session`).flush({
        session_id: 's2',
        name: 'admin-session',
        token: { access_token: adminSessionToken, token_type: 'bearer', expires_at: '2026-12-31' },
      });

      expect(service.isAdmin()).toBeTrue();
    });
  });

  describe('register', () => {
    it('should POST to register endpoint with email and password', () => {
      service.register('new@test.com', 'Str0ng!Pass').subscribe((response) => {
        expect(response.message).toBe('Registration successful');
      });

      const req = httpTesting.expectOne(`${environment.baseUrl}/api/v1/auth/register`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ email: 'new@test.com', password: 'Str0ng!Pass' });
      req.flush({ message: 'Registration successful', email: 'new@test.com' });
    });
  });

  describe('token restoration from localStorage', () => {
    it('should restore token and derive admin from JWT on construction', () => {
      const sessionToken = fakeJwt({ sub: 'sess-1', type: 'session', is_admin: true });
      localStorage.setItem('token', sessionToken);

      TestBed.resetTestingModule();
      TestBed.configureTestingModule({
        providers: [
          provideHttpClient(),
          provideHttpClientTesting(),
          provideRouter([]),
        ],
      });
      const freshService = TestBed.inject(AuthService);

      expect(freshService.isLoggedIn()).toBeTrue();
      expect(freshService.token()).toBe(sessionToken);
      expect(freshService.isAdmin()).toBeTrue();
    });

    it('should not be admin when token has no is_admin claim', () => {
      const sessionToken = fakeJwt({ sub: 'sess-1', type: 'session' });
      localStorage.setItem('token', sessionToken);

      TestBed.resetTestingModule();
      TestBed.configureTestingModule({
        providers: [
          provideHttpClient(),
          provideHttpClientTesting(),
          provideRouter([]),
        ],
      });
      const freshService = TestBed.inject(AuthService);

      expect(freshService.isLoggedIn()).toBeTrue();
      expect(freshService.isAdmin()).toBeFalse();
    });

    it('should not be admin when localStorage.isAdmin is true but token lacks claim', () => {
      const sessionToken = fakeJwt({ sub: 'sess-1', type: 'session' });
      localStorage.setItem('token', sessionToken);
      localStorage.setItem('isAdmin', 'true');

      TestBed.resetTestingModule();
      TestBed.configureTestingModule({
        providers: [
          provideHttpClient(),
          provideHttpClientTesting(),
          provideRouter([]),
        ],
      });
      const freshService = TestBed.inject(AuthService);

      expect(freshService.isAdmin()).toBeFalse();
    });
  });
});
