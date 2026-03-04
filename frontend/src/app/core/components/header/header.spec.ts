import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter, Router } from '@angular/router';
import { Header } from './header.component';
import { AuthService } from '../../services/auth.service';

describe('Header', () => {
  let component: Header;
  let fixture: ComponentFixture<Header>;

  beforeEach(async () => {
    localStorage.clear();
    await TestBed.configureTestingModule({
      imports: [Header],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(Header);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => localStorage.clear());

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should expose isLoggedIn signal', () => {
    expect(component.isLoggedIn()).toBeFalse();
  });

  it('should expose isAdmin signal', () => {
    expect(component.isAdmin()).toBeFalse();
  });

  it('should have navigation routes', () => {
    expect(component.routes.length).toBeGreaterThan(0);
    expect(component.routes[0].path).toContain('/app/');
  });

  it('should have admin routes', () => {
    expect(component.adminRoutes.length).toBe(1);
    expect(component.adminRoutes[0].path).toContain('admin');
  });

  it('should have user content routes', () => {
    expect(component.userContentRoutes.length).toBe(1);
  });

  describe('getTruncatedSessionId', () => {
    it('should return "No session ID" when no token', () => {
      expect(component.getTruncatedSessionId()).toBe('No session ID');
    });
  });

  describe('logout', () => {
    it('should call authService.logout', () => {
      const authService = TestBed.inject(AuthService);
      spyOn(authService, 'logout');
      component.logout();
      expect(authService.logout).toHaveBeenCalled();
    });
  });

  describe('createSession', () => {
    it('should call authService.createSession', () => {
      const authService = TestBed.inject(AuthService);
      spyOn(authService, 'createSession').and.callThrough();
      component.createSession();
      expect(authService.createSession).toHaveBeenCalled();
    });
  });
});
