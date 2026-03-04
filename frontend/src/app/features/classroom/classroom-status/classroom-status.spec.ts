import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { ClassroomStatus } from './classroom-status';
import { ScenarioService } from '../../../core/services/scenario.service';
import { Scenario } from '../../../core/models/scenario.model';
import { Agent } from '../../../core/models/agent.model';
import { environment } from '../../../../environments/environment';

describe('ClassroomStatus', () => {
  let component: ClassroomStatus;
  let fixture: ComponentFixture<ClassroomStatus>;
  let httpTesting: HttpTestingController;

  const mockScenario: Scenario = {
    id: 1, name: 'Test', description: 'd', overview: 'o',
    system_instructions: 'si', initial_prompt: 'ip', teaching_objectives: 'to',
  };

  beforeEach(async () => {
    localStorage.clear();
    localStorage.setItem('rehearsed_current_scenario', JSON.stringify(mockScenario));

    await TestBed.configureTestingModule({
      imports: [ClassroomStatus],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
      ],
    }).compileComponents();

    httpTesting = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(ClassroomStatus);
    component = fixture.componentInstance;
  });

  afterEach(() => {
    httpTesting.verify();
    localStorage.clear();
  });

  function flushInit() {
    fixture.detectChanges();
    httpTesting.expectOne(`${environment.baseUrl}/api/v1/scenario/1/agents`).flush([]);
  }

  it('should create', () => {
    flushInit();
    expect(component).toBeTruthy();
  });

  it('should load agents on init when scenario is set', () => {
    const mockAgents: Agent[] = [{
      id: 'a1', name: 'Alice', scenario_id: 1, agent_personality_id: 1,
      voice: 'v', display_text_color: 'teal', objective: '', instructions: '',
      constraints: '', context: '',
    }];
    fixture.detectChanges();
    httpTesting.expectOne(`${environment.baseUrl}/api/v1/scenario/1/agents`).flush(mockAgents);
  });

  describe('getAvatarUrl', () => {
    it('should return empty string when no avatar_gcs_uri', () => {
      flushInit();
      const agent = { id: 'a1', name: 'A' } as Agent;
      expect(component.getAvatarUrl(agent)).toBe('');
    });

    it('should convert GCS URI to HTTP URL', () => {
      flushInit();
      const agent = { avatar_gcs_uri: 'gs://bucket/avatar.png' } as Agent;
      expect(component.getAvatarUrl(agent)).toContain('storage.cloud.google.com');
    });

    it('should prepend / for non-GCS avatar paths', () => {
      flushInit();
      const agent = { avatar_gcs_uri: 'avatars/alice.png' } as Agent;
      expect(component.getAvatarUrl(agent)).toBe('/avatars/alice.png');
    });
  });

  describe('getColorClass', () => {
    it('should return default for undefined color', () => {
      flushInit();
      expect(component.getColorClass(undefined)).toBe('student-teal');
    });

    it('should map known colors', () => {
      flushInit();
      expect(component.getColorClass('teal')).toBe('student-teal');
      expect(component.getColorClass('light purple')).toBe('student-light-purple');
      expect(component.getColorClass('coral')).toBe('student-coral');
    });

    it('should return default for unknown colors', () => {
      flushInit();
      expect(component.getColorClass('pink')).toBe('student-teal');
    });

    it('should be case-insensitive', () => {
      flushInit();
      expect(component.getColorClass('TEAL')).toBe('student-teal');
      expect(component.getColorClass('Light Blue')).toBe('student-light-blue');
    });
  });
});
