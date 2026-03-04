import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { provideAnimations } from '@angular/platform-browser/animations';
import { provideRouter } from '@angular/router';
import { AdminFeedback } from './admin-feedback';
import { environment } from '../../../environments/environment';

describe('AdminFeedback', () => {
  let component: AdminFeedback;
  let fixture: ComponentFixture<AdminFeedback>;
  let httpTesting: HttpTestingController;

  beforeEach(async () => {
    localStorage.clear();
    await TestBed.configureTestingModule({
      imports: [AdminFeedback],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideAnimations(),
        provideRouter([]),
      ],
    }).compileComponents();

    httpTesting = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(AdminFeedback);
    component = fixture.componentInstance;
  });

  afterEach(() => {
    httpTesting.verify();
    localStorage.clear();
  });

  function flushInit() {
    fixture.detectChanges();
    httpTesting.expectOne(`${environment.baseUrl}/api/v1/admin/feedback`).flush([]);
    httpTesting.expectOne(`${environment.baseUrl}/api/v1/scenario/get-all`).flush([]);
  }

  it('should create', () => {
    flushInit();
    expect(component).toBeTruthy();
  });

  it('should load data on init via forkJoin', () => {
    flushInit();
    expect(component.feedbacks()).toEqual([]);
    expect(component.scenarios()).toEqual([]);
    expect(component.isLoading()).toBeFalse();
  });

  it('should have feedback types', () => {
    flushInit();
    expect(component.feedbackTypes).toEqual(['inline', 'summary']);
  });

  it('should toggle create form', () => {
    flushInit();
    component.toggleCreateForm();
    expect(component.showCreateForm()).toBeTrue();
    component.toggleCreateForm();
    expect(component.showCreateForm()).toBeFalse();
  });

  describe('getFeedbackTypeLabel', () => {
    it('should return Inline for inline type', () => {
      flushInit();
      expect(component.getFeedbackTypeLabel('inline')).toBe('Inline');
    });

    it('should return Summary for summary type', () => {
      flushInit();
      expect(component.getFeedbackTypeLabel('summary')).toBe('Summary');
    });
  });

  describe('truncateText', () => {
    it('should return dash for empty text', () => {
      flushInit();
      expect(component.truncateText('')).toBe('-');
    });

    it('should return text as-is when short', () => {
      flushInit();
      expect(component.truncateText('short')).toBe('short');
    });

    it('should truncate long text', () => {
      flushInit();
      const longText = 'a'.repeat(150);
      const result = component.truncateText(longText, 100);
      expect(result.length).toBe(103);
      expect(result.endsWith('...')).toBeTrue();
    });
  });

  describe('getScenarioName', () => {
    it('should return Unknown for missing scenario', () => {
      flushInit();
      expect(component.getScenarioName(999)).toBe('Unknown');
    });
  });

  describe('formatDate', () => {
    it('should return N/A for null', () => {
      flushInit();
      expect(component.formatDate(null)).toBe('N/A');
    });
  });
});
