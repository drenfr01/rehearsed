import { Component, DestroyRef, inject, signal, computed, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { ScenarioService } from '../../core/services/scenario.service';
import { Scenario } from '../../core/models/scenario.model';
import { Agent } from '../../core/models/agent.model';
import { gcsUriToHttpUrl } from '../../core/utils/gcs-uri.util';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-one-on-one-setup',
  imports: [
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatSelectModule,
    MatFormFieldModule,
    CommonModule,
    FormsModule,
  ],
  templateUrl: './one-on-one-setup.html',
  styleUrl: './one-on-one-setup.css',
})
export class OneOnOneSetup implements OnInit {
  private router = inject(Router);
  private destroyRef = inject(DestroyRef);
  private scenarioService = inject(ScenarioService);

  protected isLoading = signal(false);
  protected error = signal<string>('');
  protected scenarios = signal<Scenario[]>([]);
  protected agents = signal<Agent[]>([]);
  protected selectedScenario = signal<Scenario | null>(null);
  protected selectedAgent = signal<Agent | null>(null);

  protected canBegin = computed(() =>
    this.selectedScenario() !== null && this.selectedAgent() !== null
  );

  ngOnInit() {
    this.loadScenarios();
  }

  private loadScenarios() {
    this.isLoading.set(true);
    const sub = this.scenarioService.getScenarios().subscribe({
      next: (scenarios) => {
        this.scenarios.set(scenarios);
        this.isLoading.set(false);
      },
      error: (err: Error) => {
        this.error.set(err.message);
        this.isLoading.set(false);
      },
    });
    this.destroyRef.onDestroy(() => sub.unsubscribe());
  }

  onScenarioChange(scenario: Scenario) {
    this.selectedScenario.set(scenario);
    this.selectedAgent.set(null);
    this.agents.set([]);
    this.loadAgents(scenario.id);
  }

  private loadAgents(scenarioId: number) {
    const sub = this.scenarioService.getAgentsByScenario(scenarioId).subscribe({
      next: (agents) => this.agents.set(agents),
      error: (err: Error) => this.error.set(`Failed to load agents: ${err.message}`),
    });
    this.destroyRef.onDestroy(() => sub.unsubscribe());
  }

  onAgentSelect(agent: Agent) {
    this.selectedAgent.set(agent);
  }

  getAvatarUrl(agent: Agent): string {
    if (agent.avatar_gcs_uri) {
      if (agent.avatar_gcs_uri.startsWith('gs://')) {
        return gcsUriToHttpUrl(agent.avatar_gcs_uri);
      }
      return `/${agent.avatar_gcs_uri}`;
    }
    return '';
  }

  onBegin() {
    const scenario = this.selectedScenario();
    const agent = this.selectedAgent();
    if (!scenario || !agent) return;

    this.isLoading.set(true);
    const sub = this.scenarioService.setCurrentScenario(scenario.id).subscribe({
      complete: () => {
        this.isLoading.set(false);
        this.router.navigate(['/app/one-on-one'], {
          queryParams: {
            scenarioId: scenario.id,
            agentId: agent.id,
          },
        });
      },
      error: (err: Error) => {
        this.error.set(err.message);
        this.isLoading.set(false);
      },
    });
    this.destroyRef.onDestroy(() => sub.unsubscribe());
  }
}
