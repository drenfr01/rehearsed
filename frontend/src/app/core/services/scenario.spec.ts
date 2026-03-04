import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { ScenarioService } from './scenario.service';
import { environment } from '../../../environments/environment';
import { Scenario } from '../models/scenario.model';

describe('ScenarioService', () => {
  let service: ScenarioService;
  let httpTesting: HttpTestingController;

  const mockScenario: Scenario = {
    id: 1,
    name: 'Test Scenario',
    description: 'A test scenario',
    overview: 'Overview',
    system_instructions: 'Instructions',
    initial_prompt: 'Hello class',
    teaching_objectives: 'Teach something',
  };

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(ScenarioService);
    httpTesting = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpTesting.verify();
    localStorage.clear();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should start with empty scenarios', () => {
    expect(service.loadedScenarios()).toEqual([]);
  });

  it('should start with null current scenario when nothing stored', () => {
    expect(service.loadedCurrentScenario()).toBeNull();
  });

  describe('getScenarios', () => {
    it('should fetch scenarios and update signal', () => {
      const mockScenarios = [mockScenario];

      service.getScenarios().subscribe((scenarios) => {
        expect(scenarios).toEqual(mockScenarios);
      });

      const req = httpTesting.expectOne(`${environment.baseUrl}/api/v1/scenario/get-all`);
      expect(req.request.method).toBe('GET');
      req.flush(mockScenarios);

      expect(service.loadedScenarios()).toEqual(mockScenarios);
    });
  });

  describe('setCurrentScenario', () => {
    it('should POST to set-current-by-id and update signal', () => {
      service.setCurrentScenario(1).subscribe((scenario) => {
        expect(scenario).toEqual(mockScenario);
      });

      const req = httpTesting.expectOne(`${environment.baseUrl}/api/v1/scenario/set-current-by-id`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ scenario_id: 1 });
      req.flush(mockScenario);

      expect(service.loadedCurrentScenario()).toEqual(mockScenario);
    });
  });

  describe('getAgentsByScenario', () => {
    it('should fetch agents for a scenario', () => {
      const mockAgents = [{ id: 'a1', name: 'Agent1', scenario_id: 1 }];

      service.getAgentsByScenario(1).subscribe((agents) => {
        expect(agents.length).toBe(1);
      });

      const req = httpTesting.expectOne(`${environment.baseUrl}/api/v1/scenario/1/agents`);
      expect(req.request.method).toBe('GET');
      req.flush(mockAgents);
    });
  });

  describe('localStorage persistence', () => {
    it('should load current scenario from localStorage', () => {
      localStorage.setItem('rehearsed_current_scenario', JSON.stringify(mockScenario));

      TestBed.resetTestingModule();
      TestBed.configureTestingModule({
        providers: [provideHttpClient(), provideHttpClientTesting()],
      });
      const freshService = TestBed.inject(ScenarioService);

      expect(freshService.loadedCurrentScenario()).toEqual(mockScenario);
    });

    it('should handle corrupted localStorage gracefully', () => {
      localStorage.setItem('rehearsed_current_scenario', 'bad-json');

      TestBed.resetTestingModule();
      TestBed.configureTestingModule({
        providers: [provideHttpClient(), provideHttpClientTesting()],
      });
      const freshService = TestBed.inject(ScenarioService);

      expect(freshService.loadedCurrentScenario()).toBeNull();
    });
  });
});
