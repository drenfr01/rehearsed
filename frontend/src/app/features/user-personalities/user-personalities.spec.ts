import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { provideAnimations } from '@angular/platform-browser/animations';
import { provideRouter } from '@angular/router';
import { UserPersonalities } from './user-personalities';
import { environment } from '../../../environments/environment';

describe('UserPersonalities', () => {
  let component: UserPersonalities;
  let fixture: ComponentFixture<UserPersonalities>;
  let httpTesting: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [UserPersonalities],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideAnimations(),
        provideRouter([]),
      ],
    }).compileComponents();

    httpTesting = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(UserPersonalities);
    component = fixture.componentInstance;
  });

  afterEach(() => {
    httpTesting.verify();
  });

  function flushInit() {
    fixture.detectChanges();
    httpTesting.expectOne(`${environment.baseUrl}/api/v1/user-content/agent-personalities`).flush([]);
  }

  it('should create', () => {
    flushInit();
    expect(component).toBeTruthy();
  });

  it('should load personalities on init', () => {
    const mockData = [{ id: 1, name: 'Curious', personality_description: 'desc' }];
    fixture.detectChanges();
    httpTesting.expectOne(`${environment.baseUrl}/api/v1/user-content/agent-personalities`).flush(mockData);
    expect(component.personalities().length).toBe(1);
    expect(component.isLoading()).toBeFalse();
  });

  it('should toggle create form', () => {
    flushInit();
    component.toggleCreateForm();
    expect(component.showCreateForm()).toBeTrue();
    component.toggleCreateForm();
    expect(component.showCreateForm()).toBeFalse();
  });

  it('should have form with name and personality_description', () => {
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

    it('should format valid date', () => {
      flushInit();
      expect(component.formatDate('2025-01-01')).not.toBe('N/A');
    });
  });
});
