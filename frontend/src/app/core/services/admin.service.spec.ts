import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { AdminService } from './admin.service';
import { environment } from '../../../environments/environment';

describe('AdminService', () => {
  let service: AdminService;
  let httpTesting: HttpTestingController;
  const baseUrl = `${environment.baseUrl}/api/v1/admin`;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(AdminService);
    httpTesting = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpTesting.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  // ========== User Methods ==========

  describe('User methods', () => {
    it('getAllUsers should GET /users', () => {
      service.getAllUsers().subscribe((users) => {
        expect(users.length).toBe(1);
      });
      const req = httpTesting.expectOne(`${baseUrl}/users`);
      expect(req.request.method).toBe('GET');
      req.flush([{ id: 1, email: 'a@b.com', is_admin: false, is_approved: true, created_at: '' }]);
    });

    it('getUser should GET /users/:id', () => {
      service.getUser(5).subscribe((user) => {
        expect(user.id).toBe(5);
      });
      const req = httpTesting.expectOne(`${baseUrl}/users/5`);
      expect(req.request.method).toBe('GET');
      req.flush({ id: 5, email: 'u@t.com', is_admin: false, is_approved: true, created_at: '' });
    });

    it('createUser should POST /users', () => {
      const userData = { email: 'new@t.com', password: 'pass' };
      service.createUser(userData).subscribe();
      const req = httpTesting.expectOne(`${baseUrl}/users`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(userData);
      req.flush({ id: 1, email: 'new@t.com', is_admin: false, is_approved: false, created_at: '' });
    });

    it('updateUser should PUT /users/:id with query params', () => {
      service.updateUser(3, 'new@t.com', true).subscribe();
      const req = httpTesting.expectOne((r) => r.url === `${baseUrl}/users/3`);
      expect(req.request.method).toBe('PUT');
      expect(req.request.params.get('email')).toBe('new@t.com');
      expect(req.request.params.get('is_admin')).toBe('true');
      req.flush({ id: 3, email: 'new@t.com', is_admin: true, is_approved: true, created_at: '' });
    });

    it('updateUser should omit undefined params', () => {
      service.updateUser(3).subscribe();
      const req = httpTesting.expectOne((r) => r.url === `${baseUrl}/users/3`);
      expect(req.request.params.keys().length).toBe(0);
      req.flush({ id: 3, email: 'e@t.com', is_admin: false, is_approved: true, created_at: '' });
    });

    it('deleteUser should DELETE /users/:id', () => {
      service.deleteUser(2).subscribe((res) => {
        expect(res.message).toBe('deleted');
      });
      const req = httpTesting.expectOne(`${baseUrl}/users/2`);
      expect(req.request.method).toBe('DELETE');
      req.flush({ message: 'deleted' });
    });

    it('getPendingUsers should GET /users/pending', () => {
      service.getPendingUsers().subscribe();
      const req = httpTesting.expectOne(`${baseUrl}/users/pending`);
      expect(req.request.method).toBe('GET');
      req.flush([]);
    });

    it('approveUser should POST /users/:id/approve', () => {
      service.approveUser(7).subscribe();
      const req = httpTesting.expectOne(`${baseUrl}/users/7/approve`);
      expect(req.request.method).toBe('POST');
      req.flush({ id: 7, email: 'u@t.com', is_admin: false, is_approved: true, created_at: '' });
    });

    it('rejectUser should POST /users/:id/reject', () => {
      service.rejectUser(7).subscribe((res) => {
        expect(res.message).toBeDefined();
      });
      const req = httpTesting.expectOne(`${baseUrl}/users/7/reject`);
      expect(req.request.method).toBe('POST');
      req.flush({ message: 'rejected' });
    });
  });

  // ========== AgentPersonality Methods ==========

  describe('AgentPersonality methods', () => {
    it('getAllAgentPersonalities should GET /agent-personalities', () => {
      service.getAllAgentPersonalities().subscribe((ps) => {
        expect(ps.length).toBe(0);
      });
      const req = httpTesting.expectOne(`${baseUrl}/agent-personalities`);
      expect(req.request.method).toBe('GET');
      req.flush([]);
    });

    it('getAgentPersonality should GET /agent-personalities/:id', () => {
      service.getAgentPersonality(1).subscribe();
      const req = httpTesting.expectOne(`${baseUrl}/agent-personalities/1`);
      expect(req.request.method).toBe('GET');
      req.flush({ id: 1, name: 'Curious', personality_description: 'desc' });
    });

    it('createAgentPersonality should POST /agent-personalities', () => {
      const data = { name: 'Bold', personality_description: 'description' };
      service.createAgentPersonality(data).subscribe();
      const req = httpTesting.expectOne(`${baseUrl}/agent-personalities`);
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(data);
      req.flush({ id: 2, ...data });
    });

    it('updateAgentPersonality should PUT /agent-personalities/:id', () => {
      service.updateAgentPersonality(1, { name: 'Updated' }).subscribe();
      const req = httpTesting.expectOne(`${baseUrl}/agent-personalities/1`);
      expect(req.request.method).toBe('PUT');
      req.flush({ id: 1, name: 'Updated', personality_description: 'desc' });
    });

    it('deleteAgentPersonality should DELETE /agent-personalities/:id', () => {
      service.deleteAgentPersonality(1).subscribe();
      const req = httpTesting.expectOne(`${baseUrl}/agent-personalities/1`);
      expect(req.request.method).toBe('DELETE');
      req.flush({ message: 'deleted' });
    });
  });

  // ========== AgentVoice Methods ==========

  describe('AgentVoice methods', () => {
    it('getAgentVoices should GET /user-content/agent-voices', () => {
      service.getAgentVoices().subscribe();
      const req = httpTesting.expectOne(`${environment.baseUrl}/api/v1/user-content/agent-voices`);
      expect(req.request.method).toBe('GET');
      req.flush([]);
    });
  });

  // ========== Agent Methods ==========

  describe('Agent methods', () => {
    it('getAllAgents should GET /agents', () => {
      service.getAllAgents().subscribe();
      const req = httpTesting.expectOne(`${baseUrl}/agents`);
      expect(req.request.method).toBe('GET');
      req.flush([]);
    });

    it('getAgent should GET /agents/:id', () => {
      service.getAgent('agent-1').subscribe();
      const req = httpTesting.expectOne(`${baseUrl}/agents/agent-1`);
      expect(req.request.method).toBe('GET');
      req.flush({ id: 'agent-1', name: 'Test' });
    });

    it('createAgent should POST /agents', () => {
      const data = { id: 'a1', name: 'Agent', scenario_id: 1, agent_personality_id: 1 };
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
  });

  // ========== Scenario Methods ==========

  describe('Scenario methods', () => {
    it('getAllScenarios should GET /scenarios', () => {
      service.getAllScenarios().subscribe();
      const req = httpTesting.expectOne(`${baseUrl}/scenarios`);
      expect(req.request.method).toBe('GET');
      req.flush([]);
    });

    it('getScenario should GET /scenarios/:id', () => {
      service.getScenario(1).subscribe();
      const req = httpTesting.expectOne(`${baseUrl}/scenarios/1`);
      expect(req.request.method).toBe('GET');
      req.flush({ id: 1, name: 'S1' });
    });

    it('createScenario should POST /scenarios', () => {
      const data = { name: 'New', description: 'd', overview: 'o', system_instructions: 's', initial_prompt: 'p', teaching_objectives: 't' };
      service.createScenario(data).subscribe();
      const req = httpTesting.expectOne(`${baseUrl}/scenarios`);
      expect(req.request.method).toBe('POST');
      req.flush({ id: 1, ...data });
    });

    it('updateScenario should PUT /scenarios/:id', () => {
      service.updateScenario(1, { name: 'Updated' }).subscribe();
      const req = httpTesting.expectOne(`${baseUrl}/scenarios/1`);
      expect(req.request.method).toBe('PUT');
      req.flush({ id: 1, name: 'Updated' });
    });

    it('deleteScenario should DELETE /scenarios/:id', () => {
      service.deleteScenario(1).subscribe();
      const req = httpTesting.expectOne(`${baseUrl}/scenarios/1`);
      expect(req.request.method).toBe('DELETE');
      req.flush({ message: 'deleted' });
    });
  });

  // ========== Feedback Methods ==========

  describe('Feedback methods', () => {
    it('getAllFeedback should GET /feedback', () => {
      service.getAllFeedback().subscribe();
      const req = httpTesting.expectOne(`${baseUrl}/feedback`);
      expect(req.request.method).toBe('GET');
      req.flush([]);
    });

    it('getFeedback should GET /feedback/:id', () => {
      service.getFeedback(1).subscribe();
      const req = httpTesting.expectOne(`${baseUrl}/feedback/1`);
      expect(req.request.method).toBe('GET');
      req.flush({ id: 1 });
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
      req.flush({ id: 1, objective: 'updated' });
    });

    it('deleteFeedback should DELETE /feedback/:id', () => {
      service.deleteFeedback(1).subscribe();
      const req = httpTesting.expectOne(`${baseUrl}/feedback/1`);
      expect(req.request.method).toBe('DELETE');
      req.flush({ message: 'deleted' });
    });
  });
});
