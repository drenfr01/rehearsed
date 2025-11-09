import { inject, Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { Scenario } from '../models/scenario.model';
import { Observable, tap } from 'rxjs';

@Injectable({
  providedIn: 'root',
})
export class ScenarioService {
  private httpClient = inject(HttpClient);
  private scenarios = signal<Scenario[]>([]);
  private currentScenario = signal<Scenario | null>(null);
  loadedScenarios = this.scenarios.asReadonly();
  loadedCurrentScenario = this.currentScenario.asReadonly();

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

}
