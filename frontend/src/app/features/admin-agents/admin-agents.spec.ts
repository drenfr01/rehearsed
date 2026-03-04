import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { provideAnimations } from '@angular/platform-browser/animations';
import { provideRouter } from '@angular/router';
import { AdminAgents } from './admin-agents';
import { environment } from '../../../environments/environment';

describe('AdminAgents', () => {
  let component: AdminAgents;
  let fixture: ComponentFixture<AdminAgents>;
  let httpTesting: HttpTestingController;
  const adminUrl = `${environment.baseUrl}/api/v1/admin`;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AdminAgents],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideAnimations(),
        provideRouter([]),
      ],
    }).compileComponents();

    httpTesting = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(AdminAgents);
    component = fixture.componentInstance;
  });

  afterEach(() => {
    httpTesting.verify();
  });

  function flushInit() {
    fixture.detectChanges();
    httpTesting.expectOne(`${adminUrl}/agents`).flush([]);
    httpTesting.expectOne(`${adminUrl}/scenarios`).flush([]);
    httpTesting.expectOne(`${adminUrl}/agent-personalities`).flush([]);
    httpTesting.expectOne(`${environment.baseUrl}/api/v1/user-content/agent-voices`).flush([]);
  }

  it('should create', () => {
    flushInit();
    expect(component).toBeTruthy();
  });

  it('should load all data on init', () => {
    flushInit();
    expect(component.agents()).toEqual([]);
    expect(component.scenarios()).toEqual([]);
    expect(component.personalities()).toEqual([]);
    expect(component.voices()).toEqual([]);
    expect(component.isLoading()).toBeFalse();
  });

  it('should toggle create form', () => {
    flushInit();
    expect(component.showCreateForm()).toBeFalse();
    component.toggleCreateForm();
    expect(component.showCreateForm()).toBeTrue();
  });

  it('should have create form with required fields', () => {
    flushInit();
    expect(component.createAgentForm.controls['id']).toBeTruthy();
    expect(component.createAgentForm.controls['name']).toBeTruthy();
    expect(component.createAgentForm.controls['scenario_id']).toBeTruthy();
    expect(component.createAgentForm.controls['agent_personality_id']).toBeTruthy();
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
  });
});
