import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { provideAnimations } from '@angular/platform-browser/animations';
import { provideRouter } from '@angular/router';
import { UserScenarios } from './user-scenarios';
import { environment } from '../../../environments/environment';

describe('UserScenarios', () => {
  let component: UserScenarios;
  let fixture: ComponentFixture<UserScenarios>;
  let httpTesting: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [UserScenarios],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideAnimations(),
        provideRouter([]),
      ],
    }).compileComponents();

    httpTesting = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(UserScenarios);
    component = fixture.componentInstance;
  });

  afterEach(() => {
    httpTesting.verify();
  });

  function flushInit() {
    fixture.detectChanges();
    httpTesting.expectOne(`${environment.baseUrl}/api/v1/user-content/scenarios`).flush([]);
  }

  it('should create', () => {
    flushInit();
    expect(component).toBeTruthy();
  });

  it('should load scenarios on init', () => {
    const mockData = [{ id: 1, name: 'S1' }];
    fixture.detectChanges();
    httpTesting.expectOne(`${environment.baseUrl}/api/v1/user-content/scenarios`).flush(mockData);
    expect(component.scenarios().length).toBe(1);
    expect(component.isLoading()).toBeFalse();
  });

  it('should toggle create form', () => {
    flushInit();
    component.toggleCreateForm();
    expect(component.showCreateForm()).toBeTrue();
  });

  it('should have form with required scenario fields', () => {
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
    it('should return N/A for null', () => {
      flushInit();
      expect(component.formatDate(null)).toBe('N/A');
    });

    it('should format valid date', () => {
      flushInit();
      expect(component.formatDate('2025-03-15')).not.toBe('N/A');
    });
  });
});
