import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { UserContentService } from './user-content.service';
import { environment } from '../../../environments/environment';

describe('UserContentService', () => {
  let service: UserContentService;
  let httpTesting: HttpTestingController;
  const baseUrl = `${environment.baseUrl}/api/v1/user-content`;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(UserContentService);
    httpTesting = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpTesting.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  // ========== Scenario Methods ==========

  describe('Scenario methods', () => {
    it('getMyScenarios should GET /scenarios', () => {
      service.getMyScenarios().subscribe((s) => expect(s).toEqual([]));
      const req = httpTesting.expectOne(`${baseUrl}/scenarios`);
      expect(req.request.method).toBe('GET');
      req.flush([]);
    });

    it('createScenario should POST /scenarios', () => {
      const data = { name: 'S', description: 'd', overview: 'o', system_instructions: 'si', initial_prompt: 'ip', teaching_objectives: 'to' };
      service.createScenario(data).subscribe();
      const req = httpTesting.expectOne(`${baseUrl}/scenarios`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(data);
      req.flush({ id: 1, ...data });
    });

    it('updateScenario should PUT /scenarios/:id', () => {
      service.updateScenario(1, { name: 'Updated' }).subscribe();
      const req = httpTesting.expectOne(`${baseUrl}/scenarios/1`);
      expect(req.request.method).toBe('PUT');
      req.flush({ id: 1, name: 'Updated' });
    });

    it('deleteScenario should DELETE /scenarios/:id', () => {
      service.deleteScenario(1).subscribe((r) => expect(r.message).toBeDefined());
      const req = httpTesting.expectOne(`${baseUrl}/scenarios/1`);
      expect(req.request.method).toBe('DELETE');
      req.flush({ message: 'deleted' });
    });

    it('copyGlobalScenario should POST /scenarios/:id/copy', () => {
      service.copyGlobalScenario(5).subscribe();
      const req = httpTesting.expectOne(`${baseUrl}/scenarios/5/copy`);
      expect(req.request.method).toBe('POST');
      req.flush({ id: 10, name: 'Copied' });
    });
  });

  // ========== AgentPersonality Methods ==========

  describe('AgentPersonality methods', () => {
    it('getMyAgentPersonalities should GET /agent-personalities', () => {
      service.getMyAgentPersonalities().subscribe();
      const req = httpTesting.expectOne(`${baseUrl}/agent-personalities`);
      expect(req.request.method).toBe('GET');
      req.flush([]);
    });

    it('createAgentPersonality should POST /agent-personalities', () => {
      const data = { name: 'P', personality_description: 'desc' };
      service.createAgentPersonality(data).subscribe();
      const req = httpTesting.expectOne(`${baseUrl}/agent-personalities`);
      expect(req.request.method).toBe('POST');
      req.flush({ id: 1, ...data });
    });

    it('updateAgentPersonality should PUT /agent-personalities/:id', () => {
      service.updateAgentPersonality(1, { name: 'U' }).subscribe();
      const req = httpTesting.expectOne(`${baseUrl}/agent-personalities/1`);
      expect(req.request.method).toBe('PUT');
      req.flush({ id: 1, name: 'U' });
    });

    it('deleteAgentPersonality should DELETE /agent-personalities/:id', () => {
      service.deleteAgentPersonality(1).subscribe();
      const req = httpTesting.expectOne(`${baseUrl}/agent-personalities/1`);
      expect(req.request.method).toBe('DELETE');
      req.flush({ message: 'deleted' });
    });

    it('copyGlobalAgentPersonality should POST /agent-personalities/:id/copy', () => {
      service.copyGlobalAgentPersonality(3).subscribe();
      const req = httpTesting.expectOne(`${baseUrl}/agent-personalities/3/copy`);
      expect(req.request.method).toBe('POST');
      req.flush({ id: 10, name: 'Copied' });
    });
  });

  // ========== AgentVoice Methods ==========

  describe('AgentVoice methods', () => {
    it('getAgentVoices should GET /agent-voices', () => {
      service.getAgentVoices().subscribe();
      const req = httpTesting.expectOne(`${baseUrl}/agent-voices`);
      expect(req.request.method).toBe('GET');
      req.flush([{ id: 1, voice_name: 'Kore' }]);
    });
  });

  // ========== Agent Methods ==========

  describe('Agent methods', () => {
    it('getMyAgents should GET /agents', () => {
      service.getMyAgents().subscribe();
      const req = httpTesting.expectOne(`${baseUrl}/agents`);
      expect(req.request.method).toBe('GET');
      req.flush([]);
    });

    it('createAgent should POST /agents', () => {
      const data = { id: 'a1', name: 'A', scenario_id: 1, agent_personality_id: 1 };
      service.createAgent(data).subscribe();
      const req = httpTesting.expectOne(`${baseUrl}/agents`);
      expect(req.request.method).toBe('POST');
      req.flush({ ...data });
    });

    it('updateAgent should PUT /agents/:id', () => {
      service.updateAgent('a1', { name: 'Updated' }).subscribe();
      const req = httpTesting.expectOne(`${baseUrl}/agents/a1`);
      expect(req.request.method).toBe('PUT');
      req.flush({ id: 'a1', name: 'Updated' });
    });

    it('deleteAgent should DELETE /agents/:id', () => {
      service.deleteAgent('a1').subscribe();
      const req = httpTesting.expectOne(`${baseUrl}/agents/a1`);
      expect(req.request.method).toBe('DELETE');
      req.flush({ message: 'deleted' });
    });

    it('copyGlobalAgent should POST /agents/:id/copy with target_scenario_id param', () => {
      service.copyGlobalAgent('a1', 5).subscribe();
      const req = httpTesting.expectOne((r) => r.url === `${baseUrl}/agents/a1/copy`);
      expect(req.request.method).toBe('POST');
      expect(req.request.params.get('target_scenario_id')).toBe('5');
      req.flush({ id: 'a1-copy', name: 'Copied' });
    });
  });

  // ========== Feedback Methods ==========

  describe('Feedback methods', () => {
    it('getMyFeedback should GET /feedback', () => {
      service.getMyFeedback().subscribe();
      const req = httpTesting.expectOne(`${baseUrl}/feedback`);
      expect(req.request.method).toBe('GET');
      req.flush([]);
    });

    it('createFeedback should POST /feedback', () => {
      const data = { feedback_type: 'inline' as const, scenario_id: 1, objective: 'o', instructions: 'i', constraints: 'c', context: 'ctx' };
      service.createFeedback(data).subscribe();
      const req = httpTesting.expectOne(`${baseUrl}/feedback`);
      expect(req.request.method).toBe('POST');
      req.flush({ id: 1, ...data });
    });

    it('updateFeedback should PUT /feedback/:id', () => {
      service.updateFeedback(1, { objective: 'updated' }).subscribe();
      const req = httpTesting.expectOne(`${baseUrl}/feedback/1`);
      expect(req.request.method).toBe('PUT');
      req.flush({ id: 1 });
    });

    it('deleteFeedback should DELETE /feedback/:id', () => {
      service.deleteFeedback(1).subscribe();
      const req = httpTesting.expectOne(`${baseUrl}/feedback/1`);
      expect(req.request.method).toBe('DELETE');
      req.flush({ message: 'deleted' });
    });

    it('copyGlobalFeedback should POST /feedback/:id/copy', () => {
      service.copyGlobalFeedback(2).subscribe();
      const req = httpTesting.expectOne(`${baseUrl}/feedback/2/copy`);
      expect(req.request.method).toBe('POST');
      req.flush({ id: 10 });
    });
  });
});
