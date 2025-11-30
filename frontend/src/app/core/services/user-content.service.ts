import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { Agent, AgentCreate, AgentUpdate, AgentPersonality, AgentPersonalityCreate, AgentPersonalityUpdate, AgentVoice } from '../models/agent.model';
import { Scenario, ScenarioCreate, ScenarioUpdate } from '../models/scenario.model';
import { Feedback, FeedbackCreate, FeedbackUpdate } from '../models/feedback.model';

@Injectable({
  providedIn: 'root',
})
export class UserContentService {
  private httpClient = inject(HttpClient);
  private baseUrl = `${environment.baseUrl}/api/v1/user-content`;

  // ========== Scenario Methods ==========

  /**
   * Get all user's local scenarios
   */
  getMyScenarios(): Observable<Scenario[]> {
    return this.httpClient.get<Scenario[]>(`${this.baseUrl}/scenarios`);
  }

  /**
   * Create a new local scenario
   */
  createScenario(scenarioData: ScenarioCreate): Observable<Scenario> {
    return this.httpClient.post<Scenario>(`${this.baseUrl}/scenarios`, scenarioData);
  }

  /**
   * Update a local scenario
   */
  updateScenario(scenarioId: number, scenarioData: ScenarioUpdate): Observable<Scenario> {
    return this.httpClient.put<Scenario>(`${this.baseUrl}/scenarios/${scenarioId}`, scenarioData);
  }

  /**
   * Delete a local scenario
   */
  deleteScenario(scenarioId: number): Observable<{ message: string }> {
    return this.httpClient.delete<{ message: string }>(`${this.baseUrl}/scenarios/${scenarioId}`);
  }

  /**
   * Copy a global scenario to user's local scenarios
   */
  copyGlobalScenario(scenarioId: number): Observable<Scenario> {
    return this.httpClient.post<Scenario>(`${this.baseUrl}/scenarios/${scenarioId}/copy`, {});
  }

  // ========== AgentPersonality Methods ==========

  /**
   * Get all user's local agent personalities
   */
  getMyAgentPersonalities(): Observable<AgentPersonality[]> {
    return this.httpClient.get<AgentPersonality[]>(`${this.baseUrl}/agent-personalities`);
  }

  /**
   * Create a new local agent personality
   */
  createAgentPersonality(personalityData: AgentPersonalityCreate): Observable<AgentPersonality> {
    return this.httpClient.post<AgentPersonality>(`${this.baseUrl}/agent-personalities`, personalityData);
  }

  /**
   * Update a local agent personality
   */
  updateAgentPersonality(personalityId: number, personalityData: AgentPersonalityUpdate): Observable<AgentPersonality> {
    return this.httpClient.put<AgentPersonality>(`${this.baseUrl}/agent-personalities/${personalityId}`, personalityData);
  }

  /**
   * Delete a local agent personality
   */
  deleteAgentPersonality(personalityId: number): Observable<{ message: string }> {
    return this.httpClient.delete<{ message: string }>(`${this.baseUrl}/agent-personalities/${personalityId}`);
  }

  /**
   * Copy a global agent personality to user's local personalities
   */
  copyGlobalAgentPersonality(personalityId: number): Observable<AgentPersonality> {
    return this.httpClient.post<AgentPersonality>(`${this.baseUrl}/agent-personalities/${personalityId}/copy`, {});
  }

  // ========== AgentVoice Methods ==========

  /**
   * Get all available agent voices
   */
  getAgentVoices(): Observable<AgentVoice[]> {
    return this.httpClient.get<AgentVoice[]>(`${this.baseUrl}/agent-voices`);
  }

  // ========== Agent Methods ==========

  /**
   * Get all user's local agents
   */
  getMyAgents(): Observable<Agent[]> {
    return this.httpClient.get<Agent[]>(`${this.baseUrl}/agents`);
  }

  /**
   * Create a new local agent
   */
  createAgent(agentData: AgentCreate): Observable<Agent> {
    return this.httpClient.post<Agent>(`${this.baseUrl}/agents`, agentData);
  }

  /**
   * Update a local agent
   */
  updateAgent(agentId: string, agentData: AgentUpdate): Observable<Agent> {
    return this.httpClient.put<Agent>(`${this.baseUrl}/agents/${agentId}`, agentData);
  }

  /**
   * Delete a local agent
   */
  deleteAgent(agentId: string): Observable<{ message: string }> {
    return this.httpClient.delete<{ message: string }>(`${this.baseUrl}/agents/${agentId}`);
  }

  /**
   * Copy a global agent to user's local agents
   */
  copyGlobalAgent(agentId: string, targetScenarioId: number): Observable<Agent> {
    const params = new HttpParams().set('target_scenario_id', targetScenarioId.toString());
    return this.httpClient.post<Agent>(`${this.baseUrl}/agents/${agentId}/copy`, {}, { params });
  }

  // ========== Feedback Methods ==========

  /**
   * Get all user's local feedback
   */
  getMyFeedback(): Observable<Feedback[]> {
    return this.httpClient.get<Feedback[]>(`${this.baseUrl}/feedback`);
  }

  /**
   * Create a new local feedback
   */
  createFeedback(feedbackData: FeedbackCreate): Observable<Feedback> {
    return this.httpClient.post<Feedback>(`${this.baseUrl}/feedback`, feedbackData);
  }

  /**
   * Update a local feedback
   */
  updateFeedback(feedbackId: number, feedbackData: FeedbackUpdate): Observable<Feedback> {
    return this.httpClient.put<Feedback>(`${this.baseUrl}/feedback/${feedbackId}`, feedbackData);
  }

  /**
   * Delete a local feedback
   */
  deleteFeedback(feedbackId: number): Observable<{ message: string }> {
    return this.httpClient.delete<{ message: string }>(`${this.baseUrl}/feedback/${feedbackId}`);
  }

  /**
   * Copy a global feedback to user's local feedback
   */
  copyGlobalFeedback(feedbackId: number): Observable<Feedback> {
    return this.httpClient.post<Feedback>(`${this.baseUrl}/feedback/${feedbackId}/copy`, {});
  }
}

