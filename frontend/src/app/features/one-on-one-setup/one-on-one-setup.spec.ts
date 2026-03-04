import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { provideAnimations } from '@angular/platform-browser/animations';
import { OneOnOneSetup } from './one-on-one-setup';
import { environment } from '../../../environments/environment';
import { Agent } from '../../core/models/agent.model';

describe('OneOnOneSetup', () => {
  let component: OneOnOneSetup;
  let fixture: ComponentFixture<OneOnOneSetup>;
  let httpTesting: HttpTestingController;

  beforeEach(async () => {
    localStorage.clear();
    await TestBed.configureTestingModule({
      imports: [OneOnOneSetup],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideAnimations(),
        provideRouter([]),
      ],
    }).compileComponents();

    httpTesting = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(OneOnOneSetup);
    component = fixture.componentInstance;
  });

  afterEach(() => {
    httpTesting.verify();
    localStorage.clear();
  });

  function flushInit() {
    fixture.detectChanges();
    httpTesting.expectOne(`${environment.baseUrl}/api/v1/scenario/get-all`).flush([]);
  }

  it('should create', () => {
    flushInit();
    expect(component).toBeTruthy();
  });

  it('should load scenarios on init', () => {
    const scenarios = [{ id: 1, name: 'S1' }];
    fixture.detectChanges();
    httpTesting.expectOne(`${environment.baseUrl}/api/v1/scenario/get-all`).flush(scenarios);
  });

  describe('getAvatarUrl', () => {
    it('should return empty string when no avatar', () => {
      flushInit();
      expect(component.getAvatarUrl({ id: 'a1', name: 'A' } as Agent)).toBe('');
    });

    it('should convert GCS URI', () => {
      flushInit();
      expect(component.getAvatarUrl({ avatar_gcs_uri: 'gs://b/p.png' } as Agent)).toContain('storage.cloud.google.com');
    });

    it('should prepend / for non-GCS paths', () => {
      flushInit();
      expect(component.getAvatarUrl({ avatar_gcs_uri: 'img.png' } as Agent)).toBe('/img.png');
    });
  });
});
