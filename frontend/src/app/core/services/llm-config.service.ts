import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { AgentLlmConfig, AgentLlmConfigUpdate, LlmModel } from '../models/llm-config.model';

@Injectable({
  providedIn: 'root',
})
export class LlmConfigService {
  private httpClient = inject(HttpClient);
  private baseUrl = `${environment.baseUrl}/api/v1`;

  getLlmModels(): Observable<LlmModel[]> {
    return this.httpClient.get<LlmModel[]>(`${this.baseUrl}/llm-models`);
  }

  getAgentLlmConfigs(): Observable<AgentLlmConfig[]> {
    return this.httpClient.get<AgentLlmConfig[]>(`${this.baseUrl}/llm-config`);
  }

  updateAgentLlmConfig(update: AgentLlmConfigUpdate): Observable<AgentLlmConfig> {
    return this.httpClient.post<AgentLlmConfig>(`${this.baseUrl}/llm-config`, update);
  }
}
