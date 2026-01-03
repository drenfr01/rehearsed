import { Component, DestroyRef, inject, signal, OnInit } from '@angular/core';
import { Router, RouterModule } from '@angular/router';
import { ChatGraphService } from '../../core/services/chat-graph.service';
import { Message } from '../../core/models/chat-graph.model';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { CommonModule } from '@angular/common';
import { ScenarioService } from '../../core/services/scenario.service';
import { Scenario } from '../../core/models/scenario.model';
import { Agent } from '../../core/models/agent.model';
import { gcsUriToHttpUrl } from '../../core/utils/gcs-uri.util';

@Component({
  selector: 'app-scenario-overview',
  imports: [
    MatCardModule,
    MatButtonModule,
    MatChipsModule,
    MatIconModule,
    CommonModule,
    RouterModule,
  ],
  templateUrl: './scenario-overview.html',
  styleUrl: './scenario-overview.css',
})
export class ScenarioOverview implements OnInit {
  private router = inject(Router);
  private destroyRef = inject(DestroyRef);
  private chatGraphService = inject(ChatGraphService);
  protected isLoading = signal(false);
  protected error = signal<string>('');
  private scenarioService = inject(ScenarioService);
  
  protected scenario = signal<Scenario | null>(null);
  protected agents = signal<Agent[]>([]);

  ngOnInit() {
    const currentScenario = this.scenarioService.loadedCurrentScenario();
    if (currentScenario) {
      this.scenario.set(currentScenario);
      this.loadAgents(currentScenario.id);
    }
  }

  private loadAgents(scenarioId: number) {
    const subscription = this.scenarioService.getAgentsByScenario(scenarioId).subscribe({
      next: (agents: Agent[]) => {
        this.agents.set(agents);
      },
      error: (error: Error) => {
        console.error('Failed to load agents:', error);
      },
    });
    this.destroyRef.onDestroy(() => {
      subscription.unsubscribe();
    });
  }

  getAvatarUrl(agent: Agent): string {
    if (agent.avatar_gcs_uri) {
      return gcsUriToHttpUrl(agent.avatar_gcs_uri);
    }
    return '';
  }

  getDifficultyColor(difficulty: string): string {
    switch (difficulty) {
      case 'Beginner': return 'difficulty-beginner';
      case 'Intermediate': return 'difficulty-intermediate';
      case 'Advanced': return 'difficulty-advanced';
      default: return 'difficulty-default';
    }
  }

  onBeginSimulation() {
    if (!this.scenario()) return;
    
    this.isLoading.set(true);
    this.error.set('');
    
    const newMessage: Message = {
      role: 'user',
      content: this.scenario()!.initial_prompt,
    }
    
    // Sending initial graph request, hence the true flag
    const subscription = this.chatGraphService.sendGraphRequest({
        messages: [newMessage],
        is_resumption: false,
        resumption_text: '',
        resumption_approved: false,
    }, true).subscribe({
      error: (error: Error) => {
        this.error.set(error.message);
        this.isLoading.set(false);
      },
      complete: () => {
        this.isLoading.set(false);
        this.router.navigate(['/app/classroom']);
      },
    });
    
    this.destroyRef.onDestroy(() => {
      subscription.unsubscribe();
    });
  }
}
