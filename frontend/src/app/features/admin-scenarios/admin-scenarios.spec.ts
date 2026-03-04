import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { provideAnimations } from '@angular/platform-browser/animations';
import { provideRouter } from '@angular/router';
import { AdminScenarios } from './admin-scenarios';
import { environment } from '../../../environments/environment';

describe('AdminScenarios', () => {
  let component: AdminScenarios;
  let fixture: ComponentFixture<AdminScenarios>;
  let httpTesting: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AdminScenarios],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideAnimations(),
        provideRouter([]),
      ],
    }).compileComponents();

    httpTesting = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(AdminScenarios);
    component = fixture.componentInstance;
  });

  afterEach(() => {
    httpTesting.verify();
  });

  function flushInit() {
    fixture.detectChanges();
    httpTesting.expectOne(`${environment.baseUrl}/api/v1/admin/scenarios`).flush([]);
  }

  it('should create', () => {
    flushInit();
    expect(component).toBeTruthy();
  });

  it('should load scenarios on init', () => {
    const mockScenarios = [{ id: 1, name: 'S1', description: 'd', overview: 'o', system_instructions: 'si', initial_prompt: 'ip', teaching_objectives: 'to' }];
    fixture.detectChanges();
    httpTesting.expectOne(`${environment.baseUrl}/api/v1/admin/scenarios`).flush(mockScenarios);
    expect(component.scenarios().length).toBe(1);
    expect(component.isLoading()).toBeFalse();
  });

  it('should toggle create form', () => {
    flushInit();
    component.toggleCreateForm();
    expect(component.showCreateForm()).toBeTrue();
    component.toggleCreateForm();
    expect(component.showCreateForm()).toBeFalse();
  });

  it('should have create form with required fields', () => {
    flushInit();
    const form = component.createScenarioForm;
    expect(form.controls['name']).toBeTruthy();
    expect(form.controls['description']).toBeTruthy();
    expect(form.controls['overview']).toBeTruthy();
    expect(form.controls['system_instructions']).toBeTruthy();
    expect(form.controls['initial_prompt']).toBeTruthy();
    expect(form.controls['teaching_objectives']).toBeTruthy();
  });

  describe('formatDate', () => {
    it('should return N/A for null/undefined', () => {
      flushInit();
      expect(component.formatDate(null)).toBe('N/A');
      expect(component.formatDate(undefined)).toBe('N/A');
    });

    it('should format valid date', () => {
      flushInit();
      expect(component.formatDate('2025-06-01T00:00:00Z')).not.toBe('N/A');
    });
  });
});
