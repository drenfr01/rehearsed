import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { provideAnimations } from '@angular/platform-browser/animations';
import { provideRouter } from '@angular/router';
import { UserAgents, AGENT_DISPLAY_COLORS } from './user-agents';
import { environment } from '../../../environments/environment';

describe('UserAgents', () => {
  let component: UserAgents;
  let fixture: ComponentFixture<UserAgents>;
  let httpTesting: HttpTestingController;
  const ucUrl = `${environment.baseUrl}/api/v1/user-content`;

  beforeEach(async () => {
    localStorage.clear();
    await TestBed.configureTestingModule({
      imports: [UserAgents],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideAnimations(),
        provideRouter([]),
      ],
    }).compileComponents();

    httpTesting = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(UserAgents);
    component = fixture.componentInstance;
  });

  afterEach(() => {
    httpTesting.verify();
    localStorage.clear();
  });

  function flushInit() {
    fixture.detectChanges();
    httpTesting.expectOne(`${ucUrl}/agents`).flush([]);
    httpTesting.expectOne(`${environment.baseUrl}/api/v1/scenario/get-all`).flush([]);
    httpTesting.expectOne(`${ucUrl}/agent-personalities`).flush([]);
    httpTesting.expectOne(`${ucUrl}/agent-voices`).flush([]);
  }

  it('should create', () => {
    flushInit();
    expect(component).toBeTruthy();
  });

  it('should load all data on init', () => {
    flushInit();
    expect(component.isLoading()).toBeFalse();
    expect(component.agents()).toEqual([]);
  });

  it('should export AGENT_DISPLAY_COLORS', () => {
    expect(AGENT_DISPLAY_COLORS.length).toBeGreaterThan(0);
    expect(AGENT_DISPLAY_COLORS[0]).toEqual(jasmine.objectContaining({ value: jasmine.any(String), label: jasmine.any(String) }));
  });

  it('should toggle create form', () => {
    flushInit();
    component.toggleCreateForm();
    expect(component.showCreateForm()).toBeTrue();
  });

  describe('getScenarioName', () => {
    it('should return Unknown for missing scenario', () => {
      flushInit();
      expect(component.getScenarioName(999)).toBe('Unknown');
    });
  });

  describe('getPersonalityName', () => {
    it('should return Unknown for missing personality', () => {
      flushInit();
      expect(component.getPersonalityName(999)).toBe('Unknown');
    });
  });

  describe('formatDate', () => {
    it('should return N/A for null', () => {
      flushInit();
      expect(component.formatDate(null)).toBe('N/A');
    });

    it('should format valid date', () => {
      flushInit();
      expect(component.formatDate('2025-01-01')).not.toBe('N/A');
    });
  });
});
