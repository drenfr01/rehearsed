import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { provideAnimations } from '@angular/platform-browser/animations';
import { provideRouter } from '@angular/router';
import { AdminAppConfig } from './admin-app-config';
import { environment } from '../../../environments/environment';

describe('AdminAppConfig', () => {
  let component: AdminAppConfig;
  let fixture: ComponentFixture<AdminAppConfig>;
  let httpTesting: HttpTestingController;

  const mockModels = [
    { id: 1, name: 'gemini-3.1-pro-preview' },
    { id: 2, name: 'gemini-3.1-flash-lite-preview' },
    { id: 3, name: 'gemini-3-flash-preview' },
  ];

  const mockConfigs = [
    { agent_type: 'student_agent', llm_model_id: 3, llm_model_name: 'gemini-3-flash-preview' },
    { agent_type: 'student_choice_agent', llm_model_id: 2, llm_model_name: 'gemini-3.1-flash-lite-preview' },
    { agent_type: 'inline_feedback', llm_model_id: 3, llm_model_name: 'gemini-3-flash-preview' },
    { agent_type: 'summary_feedback', llm_model_id: 1, llm_model_name: 'gemini-3.1-pro-preview' },
  ];

  beforeEach(async () => {
    localStorage.clear();
    await TestBed.configureTestingModule({
      imports: [AdminAppConfig],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideAnimations(),
        provideRouter([]),
      ],
    }).compileComponents();

    httpTesting = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(AdminAppConfig);
    component = fixture.componentInstance;
  });

  afterEach(() => {
    httpTesting.verify();
    localStorage.clear();
  });

  function flushInit() {
    fixture.detectChanges();
    httpTesting.expectOne(`${environment.baseUrl}/api/v1/llm-models`).flush(mockModels);
    httpTesting.expectOne(`${environment.baseUrl}/api/v1/llm-config`).flush(mockConfigs);
  }

  it('should create', () => {
    flushInit();
    expect(component).toBeTruthy();
  });

  it('should load models and configs on init', () => {
    flushInit();
    expect(component.llmModels().length).toBe(3);
    expect(component.agentRows().length).toBe(4);
    expect(component.isLoading()).toBeFalse();
  });

  it('should populate agent rows with correct labels and icons', () => {
    flushInit();
    const rows = component.agentRows();
    expect(rows[0].label).toBe('Student Agent');
    expect(rows[0].icon).toBe('school');
    expect(rows[1].label).toBe('Student Choice Agent');
    expect(rows[1].icon).toBe('how_to_reg');
    expect(rows[2].label).toBe('Inline Feedback');
    expect(rows[2].icon).toBe('rate_review');
    expect(rows[3].label).toBe('Summary Feedback');
    expect(rows[3].icon).toBe('summarize');
  });

  it('should populate agent rows with selected model ids', () => {
    flushInit();
    const rows = component.agentRows();
    expect(rows[0].selectedModelId).toBe(3);
    expect(rows[1].selectedModelId).toBe(2);
    expect(rows[2].selectedModelId).toBe(3);
    expect(rows[3].selectedModelId).toBe(1);
  });

  it('should call update API on model change', () => {
    flushInit();
    const row = component.agentRows()[0];
    component.onModelChange(row, 1);

    const req = httpTesting.expectOne(`${environment.baseUrl}/api/v1/llm-config`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({
      agent_type: 'student_agent',
      llm_model_id: 1,
    });
    req.flush({
      agent_type: 'student_agent',
      llm_model_id: 1,
      llm_model_name: 'gemini-3.1-pro-preview',
    });
    expect(row.selectedModelId).toBe(1);
  });

  it('should set savingAgentType during update', () => {
    flushInit();
    const row = component.agentRows()[0];
    component.onModelChange(row, 1);
    expect(component.savingAgentType()).toBe('student_agent');

    httpTesting.expectOne(`${environment.baseUrl}/api/v1/llm-config`).flush({
      agent_type: 'student_agent',
      llm_model_id: 1,
      llm_model_name: 'gemini-3.1-pro-preview',
    });
    expect(component.savingAgentType()).toBeNull();
  });

  it('should handle load error gracefully', () => {
    fixture.detectChanges();
    httpTesting.expectOne(`${environment.baseUrl}/api/v1/llm-models`).error(new ProgressEvent('error'));
    httpTesting.expectOne(`${environment.baseUrl}/api/v1/llm-config`).error(new ProgressEvent('error'));
    expect(component.isLoading()).toBeFalse();
  });
});
