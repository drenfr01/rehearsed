import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { provideAnimations } from '@angular/platform-browser/animations';
import { provideRouter } from '@angular/router';
import { AdminAgentPersonalities } from './admin-agent-personalities';
import { environment } from '../../../environments/environment';

describe('AdminAgentPersonalities', () => {
  let component: AdminAgentPersonalities;
  let fixture: ComponentFixture<AdminAgentPersonalities>;
  let httpTesting: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AdminAgentPersonalities],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideAnimations(),
        provideRouter([]),
      ],
    }).compileComponents();

    httpTesting = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(AdminAgentPersonalities);
    component = fixture.componentInstance;
  });

  afterEach(() => {
    httpTesting.verify();
  });

  function flushInit() {
    fixture.detectChanges();
    httpTesting.expectOne(`${environment.baseUrl}/api/v1/admin/agent-personalities`).flush([]);
  }

  it('should create', () => {
    flushInit();
    expect(component).toBeTruthy();
  });

  it('should load personalities on init', () => {
    const mockPersonalities = [{ id: 1, name: 'Curious', personality_description: 'desc' }];
    fixture.detectChanges();
    httpTesting.expectOne(`${environment.baseUrl}/api/v1/admin/agent-personalities`).flush(mockPersonalities);
    expect(component.personalities()).toEqual(mockPersonalities as any);
    expect(component.isLoading()).toBeFalse();
  });

  it('should handle load error', () => {
    fixture.detectChanges();
    httpTesting.expectOne(`${environment.baseUrl}/api/v1/admin/agent-personalities`)
      .flush('error', { status: 500, statusText: 'Server Error' });
    expect(component.isLoading()).toBeFalse();
  });

  it('should toggle create form', () => {
    flushInit();
    expect(component.showCreateForm()).toBeFalse();
    component.toggleCreateForm();
    expect(component.showCreateForm()).toBeTrue();
    component.toggleCreateForm();
    expect(component.showCreateForm()).toBeFalse();
  });

  it('should have displayed columns', () => {
    flushInit();
    expect(component.displayedColumns).toContain('name');
    expect(component.displayedColumns).toContain('actions');
  });

  it('should have a create form with name and personality_description', () => {
    flushInit();
    expect(component.createPersonalityForm.controls['name']).toBeTruthy();
    expect(component.createPersonalityForm.controls['personality_description']).toBeTruthy();
  });

  describe('formatDate', () => {
    it('should return N/A for null/undefined', () => {
      flushInit();
      expect(component.formatDate(null)).toBe('N/A');
      expect(component.formatDate(undefined)).toBe('N/A');
    });

    it('should format valid date string', () => {
      flushInit();
      const result = component.formatDate('2025-01-15T10:30:00Z');
      expect(result).toBeTruthy();
      expect(result).not.toBe('N/A');
    });
  });
});
