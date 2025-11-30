import { inject, Injectable, signal, effect } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { Scenario } from '../models/scenario.model';
import { Agent } from '../models/agent.model';
import { Observable, tap } from 'rxjs';

const CURRENT_SCENARIO_KEY = 'rehearsed_current_scenario';

@Injectable({
  providedIn: 'root',
})
export class ScenarioService {
  private httpClient = inject(HttpClient);
  private scenarios = signal<Scenario[]>([]);
  private currentScenario = signal<Scenario | null>(this.loadCurrentScenarioFromStorage());
  loadedScenarios = this.scenarios.asReadonly();
  loadedCurrentScenario = this.currentScenario.asReadonly();

  constructor() {
    // Effect to persist current scenario to localStorage
    effect(() => {
      const scenario = this.currentScenario();
      if (scenario) {
        localStorage.setItem(CURRENT_SCENARIO_KEY, JSON.stringify(scenario));
      } else {
        localStorage.removeItem(CURRENT_SCENARIO_KEY);
      }
    });
  }

  private loadCurrentScenarioFromStorage(): Scenario | null {
    try {
      const stored = localStorage.getItem(CURRENT_SCENARIO_KEY);
      return stored ? JSON.parse(stored) : null;
    } catch (error) {
      console.error('Error loading scenario from localStorage:', error);
      return null;
    }
  }

  getScenarios(): Observable<Scenario[]> {
    return this.httpClient.get<Scenario[]>(`${environment.baseUrl}/api/v1/scenario/get-all`).pipe(
      tap((scenarios: Scenario[]) => {
        this.scenarios.set(scenarios);
      })
    );
  }

  setCurrentScenario(scenarioId: number): Observable<Scenario> {
    return this.httpClient.post<Scenario>(`${environment.baseUrl}/api/v1/scenario/set-current-by-id`, {
      scenario_id: scenarioId,
    }).pipe(
      tap((scenario: Scenario) => {
        this.currentScenario.set(scenario);
      })
    );
  }

  getAgentsByScenario(scenarioId: number): Observable<Agent[]> {
    return this.httpClient.get<Agent[]>(`${environment.baseUrl}/api/v1/scenario/${scenarioId}/agents`);
  }

}
