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

  loadedScenarios = this.scenarios.asReadonly();

  getScenarios(): Observable<Scenario[]> {
    return this.httpClient.get<Scenario[]>(`${environment.baseUrl}/api/v1/scenario/get-all`).pipe(
      tap((scenarios: Scenario[]) => {
        this.scenarios.set(scenarios);
      })
    );
  }

}
