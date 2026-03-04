import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { Router } from '@angular/router';
import { AuthService } from './auth.service';
import { environment } from '../../../environments/environment';

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

      // Session creation follows login
      const sessionReq = httpTesting.expectOne(`${environment.baseUrl}/api/v1/auth/session`);
      sessionReq.flush({
        session_id: 's1',
        name: 'session',
        token: { access_token: 'session-token', token_type: 'bearer', expires_at: '2026-12-31', is_admin: false },
      });

      expect(service.isLoggedIn()).toBeTrue();
    });

    it('should store token and admin status', () => {
      service.login('admin@test.com', 'pass').subscribe();

      httpTesting.expectOne(`${environment.baseUrl}/api/v1/auth/login`).flush({
        access_token: 'admin-token',
        token_type: 'bearer',
        expires_at: '2026-12-31',
        is_admin: true,
      });

      httpTesting.expectOne(`${environment.baseUrl}/api/v1/auth/session`).flush({
        session_id: 's1',
        name: 'session',
        token: { access_token: 'session-token', token_type: 'bearer', expires_at: '2026-12-31', is_admin: true },
      });

      expect(service.isAdmin()).toBeTrue();
      expect(localStorage.getItem('isAdmin')).toBe('true');
    });
  });

  describe('logout', () => {
    it('should clear tokens and navigate to root', () => {
      spyOn(router, 'navigate');
      localStorage.setItem('token', 'some-token');
      localStorage.setItem('userToken', 'some-token');
      localStorage.setItem('isAdmin', 'true');

      service.logout();

      expect(localStorage.getItem('token')).toBeNull();
      expect(localStorage.getItem('userToken')).toBeNull();
      expect(localStorage.getItem('isAdmin')).toBeNull();
      expect(service.isLoggedIn()).toBeFalse();
      expect(service.isAdmin()).toBeFalse();
      expect(router.navigate).toHaveBeenCalledWith(['/']);
    });
  });

  describe('createSession', () => {
    it('should POST to session endpoint and store session token', () => {
      service.createSession().subscribe();

      const req = httpTesting.expectOne(`${environment.baseUrl}/api/v1/auth/session`);
      expect(req.request.method).toBe('POST');
      req.flush({
        session_id: 's1',
        name: 'test',
        token: { access_token: 'new-session-token', token_type: 'bearer', expires_at: '2026-12-31', is_admin: false },
      });

      expect(localStorage.getItem('token')).toBe('new-session-token');
      expect(service.token()).toBe('new-session-token');
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
    it('should restore token from localStorage on construction', () => {
      localStorage.setItem('token', 'stored-token');
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

      expect(freshService.isLoggedIn()).toBeTrue();
      expect(freshService.token()).toBe('stored-token');
      expect(freshService.isAdmin()).toBeTrue();
    });
  });
});
