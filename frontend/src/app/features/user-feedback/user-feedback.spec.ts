import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { provideAnimations } from '@angular/platform-browser/animations';
import { provideRouter } from '@angular/router';
import { UserFeedback } from './user-feedback';
import { environment } from '../../../environments/environment';

describe('UserFeedback', () => {
  let component: UserFeedback;
  let fixture: ComponentFixture<UserFeedback>;
  let httpTesting: HttpTestingController;

  beforeEach(async () => {
    localStorage.clear();
    await TestBed.configureTestingModule({
      imports: [UserFeedback],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideAnimations(),
        provideRouter([]),
      ],
    }).compileComponents();

    httpTesting = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(UserFeedback);
    component = fixture.componentInstance;
  });

  afterEach(() => {
    httpTesting.verify();
    localStorage.clear();
  });

  function flushInit() {
    fixture.detectChanges();
    httpTesting.expectOne(`${environment.baseUrl}/api/v1/user-content/feedback`).flush([]);
    httpTesting.expectOne(`${environment.baseUrl}/api/v1/scenario/get-all`).flush([]);
  }

  it('should create', () => {
    flushInit();
    expect(component).toBeTruthy();
  });

  it('should load data on init', () => {
    flushInit();
    expect(component.feedbacks()).toEqual([]);
    expect(component.scenarios()).toEqual([]);
    expect(component.isLoading()).toBeFalse();
  });

  it('should toggle create form', () => {
    flushInit();
    component.toggleCreateForm();
    expect(component.showCreateForm()).toBeTrue();
  });

  describe('getFeedbackTypeLabel', () => {
    it('should map types correctly', () => {
      flushInit();
      expect(component.getFeedbackTypeLabel('inline')).toBe('Inline');
      expect(component.getFeedbackTypeLabel('summary')).toBe('Summary');
    });
  });

  describe('truncateText', () => {
    it('should return dash for empty', () => {
      flushInit();
      expect(component.truncateText('')).toBe('-');
    });

    it('should truncate at custom length', () => {
      flushInit();
      expect(component.truncateText('abcdefghij', 5)).toBe('abcde...');
    });
  });

  describe('getScenarioName', () => {
    it('should return Unknown for missing', () => {
      flushInit();
      expect(component.getScenarioName(1)).toBe('Unknown');
    });
  });

  describe('formatDate', () => {
    it('should return N/A for null', () => {
      flushInit();
      expect(component.formatDate(null)).toBe('N/A');
    });
  });
});
