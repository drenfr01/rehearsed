import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { User, UserCreate } from '../models/user.model';
import { Agent, AgentCreate, AgentPersonality, AgentPersonalityCreate } from '../models/agent.model';
import { Scenario, ScenarioCreate } from '../models/scenario.model';

@Injectable({
  providedIn: 'root',
})
export class AdminService {
  private httpClient = inject(HttpClient);
  private baseUrl = `${environment.baseUrl}/api/v1/admin`;

  // ========== User Methods ==========

  /**
   * Get all users in the system
   */
  getAllUsers(): Observable<User[]> {
    return this.httpClient.get<User[]>(`${this.baseUrl}/users`);
  }

  /**
   * Get a specific user by ID
   */
  getUser(userId: number): Observable<User> {
    return this.httpClient.get<User>(`${this.baseUrl}/users/${userId}`);
  }

  /**
   * Create a new user
   */
  createUser(userData: UserCreate): Observable<User> {
    return this.httpClient.post<User>(`${this.baseUrl}/users`, userData);
  }

  /**
   * Update a user
   */
  updateUser(userId: number, email?: string, isAdmin?: boolean): Observable<User> {
    let params = new HttpParams();
    if (email !== undefined) {
      params = params.set('email', email);
    }
    if (isAdmin !== undefined) {
      params = params.set('is_admin', isAdmin.toString());
    }
    return this.httpClient.put<User>(`${this.baseUrl}/users/${userId}`, null, { params });
  }

  /**
   * Delete a user
   */
  deleteUser(userId: number): Observable<{ message: string }> {
    return this.httpClient.delete<{ message: string }>(`${this.baseUrl}/users/${userId}`);
  }

  // ========== AgentPersonality Methods ==========

  /**
   * Get all agent personalities
   */
  getAllAgentPersonalities(): Observable<AgentPersonality[]> {
    return this.httpClient.get<AgentPersonality[]>(`${this.baseUrl}/agent-personalities`);
  }

  /**
   * Get a specific agent personality by ID
   */
  getAgentPersonality(personalityId: number): Observable<AgentPersonality> {
    return this.httpClient.get<AgentPersonality>(`${this.baseUrl}/agent-personalities/${personalityId}`);
  }

  /**
   * Create a new agent personality
   */
  createAgentPersonality(personalityData: AgentPersonalityCreate): Observable<AgentPersonality> {
    return this.httpClient.post<AgentPersonality>(`${this.baseUrl}/agent-personalities`, personalityData);
  }

  /**
   * Update an agent personality
   */
  updateAgentPersonality(personalityId: number, personalityData: Partial<AgentPersonalityCreate>): Observable<AgentPersonality> {
    return this.httpClient.put<AgentPersonality>(`${this.baseUrl}/agent-personalities/${personalityId}`, personalityData);
  }

  /**
   * Delete an agent personality
   */
  deleteAgentPersonality(personalityId: number): Observable<{ message: string }> {
    return this.httpClient.delete<{ message: string }>(`${this.baseUrl}/agent-personalities/${personalityId}`);
  }

  // ========== Agent Methods ==========

  /**
   * Get all agents
   */
  getAllAgents(): Observable<Agent[]> {
    return this.httpClient.get<Agent[]>(`${this.baseUrl}/agents`);
  }

  /**
   * Get a specific agent by ID
   */
  getAgent(agentId: string): Observable<Agent> {
    return this.httpClient.get<Agent>(`${this.baseUrl}/agents/${agentId}`);
  }

  /**
   * Create a new agent
   */
  createAgent(agentData: AgentCreate): Observable<Agent> {
    return this.httpClient.post<Agent>(`${this.baseUrl}/agents`, agentData);
  }

  /**
   * Update an agent
   */
  updateAgent(agentId: string, agentData: Partial<AgentCreate>): Observable<Agent> {
    return this.httpClient.put<Agent>(`${this.baseUrl}/agents/${agentId}`, agentData);
  }

  /**
   * Delete an agent
   */
  deleteAgent(agentId: string): Observable<{ message: string }> {
    return this.httpClient.delete<{ message: string }>(`${this.baseUrl}/agents/${agentId}`);
  }

  // ========== Scenario Methods ==========

  /**
   * Get all scenarios
   */
  getAllScenarios(): Observable<Scenario[]> {
    return this.httpClient.get<Scenario[]>(`${this.baseUrl}/scenarios`);
  }

  /**
   * Get a specific scenario by ID
   */
  getScenario(scenarioId: number): Observable<Scenario> {
    return this.httpClient.get<Scenario>(`${this.baseUrl}/scenarios/${scenarioId}`);
  }

  /**
   * Create a new scenario
   */
  createScenario(scenarioData: ScenarioCreate): Observable<Scenario> {
    return this.httpClient.post<Scenario>(`${this.baseUrl}/scenarios`, scenarioData);
  }

  /**
   * Update a scenario
   */
  updateScenario(scenarioId: number, scenarioData: Partial<ScenarioCreate>): Observable<Scenario> {
    return this.httpClient.put<Scenario>(`${this.baseUrl}/scenarios/${scenarioId}`, scenarioData);
  }

  /**
   * Delete a scenario
   */
  deleteScenario(scenarioId: number): Observable<{ message: string }> {
    return this.httpClient.delete<{ message: string }>(`${this.baseUrl}/scenarios/${scenarioId}`);
  }
}

