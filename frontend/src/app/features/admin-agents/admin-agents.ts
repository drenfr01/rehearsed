import { Component, DestroyRef, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatDialogModule } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { LoadingSpinner } from '../../shared/loading-spinner/loading-spinner';
import { AdminService } from '../../core/services/admin.service';
import { Agent, AgentCreate, AgentPersonality } from '../../core/models/agent.model';
import { Scenario } from '../../core/models/scenario.model';

@Component({
  selector: 'app-admin-agents',
  imports: [
    CommonModule,
    RouterModule,
    ReactiveFormsModule,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatDialogModule,
    MatSnackBarModule,
    MatTooltipModule,
    LoadingSpinner,
  ],
  templateUrl: './admin-agents.html',
  styleUrl: './admin-agents.css',
})
export class AdminAgents implements OnInit {
  private adminService = inject(AdminService);
  private destroyRef = inject(DestroyRef);
  private fb = inject(FormBuilder);
  private snackBar = inject(MatSnackBar);

  agents = signal<Agent[]>([]);
  scenarios = signal<Scenario[]>([]);
  personalities = signal<AgentPersonality[]>([]);
  displayedColumns: string[] = ['id', 'name', 'scenario', 'personality', 'voice', 'created_at', 'actions'];
  isLoading = signal(false);
  showCreateForm = signal(false);

  createAgentForm: FormGroup;
  editingAgent = signal<Agent | null>(null);
  editAgentForm: FormGroup;

  constructor() {
    this.createAgentForm = this.fb.group({
      id: ['', [Validators.required, Validators.minLength(2)]],
      name: ['', [Validators.required, Validators.minLength(2)]],
      scenario_id: [null, [Validators.required]],
      agent_personality_id: [null, [Validators.required]],
      voice: [''],
      display_text_color: [''],
      objective: [''],
      instructions: [''],
      constraints: [''],
      context: [''],
    });

    this.editAgentForm = this.fb.group({
      name: ['', [Validators.required, Validators.minLength(2)]],
      scenario_id: [null, [Validators.required]],
      agent_personality_id: [null, [Validators.required]],
      voice: [''],
      display_text_color: [''],
      objective: [''],
      instructions: [''],
      constraints: [''],
      context: [''],
    });
  }

  ngOnInit() {
    this.loadData();
  }

  loadData() {
    this.isLoading.set(true);
    
    // Load all necessary data
    const agentsSubscription = this.adminService.getAllAgents().subscribe({
      next: (agents) => {
        this.agents.set(agents);
        this.checkLoadingComplete();
      },
      error: (error) => {
        console.error('Failed to load agents', error);
        this.snackBar.open('Failed to load agents', 'Close', { duration: 3000 });
        this.checkLoadingComplete();
      },
    });

    const scenariosSubscription = this.adminService.getAllScenarios().subscribe({
      next: (scenarios) => {
        this.scenarios.set(scenarios);
        this.checkLoadingComplete();
      },
      error: (error) => {
        console.error('Failed to load scenarios', error);
        this.checkLoadingComplete();
      },
    });

    const personalitiesSubscription = this.adminService.getAllAgentPersonalities().subscribe({
      next: (personalities) => {
        this.personalities.set(personalities);
        this.checkLoadingComplete();
      },
      error: (error) => {
        console.error('Failed to load personalities', error);
        this.checkLoadingComplete();
      },
    });

    this.destroyRef.onDestroy(() => {
      agentsSubscription.unsubscribe();
      scenariosSubscription.unsubscribe();
      personalitiesSubscription.unsubscribe();
    });
  }

  private loadingCounter = 0;
  private checkLoadingComplete() {
    this.loadingCounter++;
    if (this.loadingCounter >= 3) {
      this.isLoading.set(false);
      this.loadingCounter = 0;
    }
  }

  toggleCreateForm() {
    this.showCreateForm.set(!this.showCreateForm());
    if (!this.showCreateForm()) {
      this.createAgentForm.reset();
    }
  }

  createAgent() {
    if (this.createAgentForm.valid) {
      const agentData: AgentCreate = this.createAgentForm.value;
      const subscription = this.adminService.createAgent(agentData).subscribe({
        next: (agent) => {
          this.agents.update(agents => [...agents, agent]);
          this.snackBar.open('Agent created successfully', 'Close', { duration: 3000 });
          this.createAgentForm.reset();
          this.showCreateForm.set(false);
        },
        error: (error) => {
          console.error('Failed to create agent', error);
          const errorMessage = error.error?.detail || 'Failed to create agent';
          this.snackBar.open(errorMessage, 'Close', { duration: 5000 });
        },
      });
      this.destroyRef.onDestroy(() => subscription.unsubscribe());
    }
  }

  startEdit(agent: Agent) {
    this.editingAgent.set(agent);
    this.editAgentForm.patchValue({
      name: agent.name,
      scenario_id: agent.scenario_id,
      agent_personality_id: agent.agent_personality_id,
      voice: agent.voice,
      display_text_color: agent.display_text_color,
      objective: agent.objective,
      instructions: agent.instructions,
      constraints: agent.constraints,
      context: agent.context,
    });
  }

  cancelEdit() {
    this.editingAgent.set(null);
    this.editAgentForm.reset();
  }

  saveEdit(agentId: string) {
    if (this.editAgentForm.valid) {
      const formValue = this.editAgentForm.value;
      const subscription = this.adminService.updateAgent(agentId, formValue).subscribe({
        next: (updatedAgent) => {
          this.agents.update(agents => 
            agents.map(a => a.id === agentId ? updatedAgent : a)
          );
          this.snackBar.open('Agent updated successfully', 'Close', { duration: 3000 });
          this.cancelEdit();
        },
        error: (error) => {
          console.error('Failed to update agent', error);
          const errorMessage = error.error?.detail || 'Failed to update agent';
          this.snackBar.open(errorMessage, 'Close', { duration: 5000 });
        },
      });
      this.destroyRef.onDestroy(() => subscription.unsubscribe());
    }
  }

  deleteAgent(agentId: string, name: string) {
    if (confirm(`Are you sure you want to delete agent "${name}"?`)) {
      const subscription = this.adminService.deleteAgent(agentId).subscribe({
        next: () => {
          this.agents.update(agents => agents.filter(a => a.id !== agentId));
          this.snackBar.open('Agent deleted successfully', 'Close', { duration: 3000 });
        },
        error: (error) => {
          console.error('Failed to delete agent', error);
          const errorMessage = error.error?.detail || 'Failed to delete agent';
          this.snackBar.open(errorMessage, 'Close', { duration: 5000 });
        },
      });
      this.destroyRef.onDestroy(() => subscription.unsubscribe());
    }
  }

  getScenarioName(scenarioId: number): string {
    const scenario = this.scenarios().find(s => s.id === scenarioId);
    return scenario?.name || 'Unknown';
  }

  getPersonalityName(personalityId: number): string {
    const personality = this.personalities().find(p => p.id === personalityId);
    return personality?.name || 'Unknown';
  }

  formatDate(dateString: string | null | undefined): string {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString();
  }
}

