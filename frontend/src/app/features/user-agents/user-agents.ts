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
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { LoadingSpinner } from '../../shared/loading-spinner/loading-spinner';
import { UserContentService } from '../../core/services/user-content.service';
import { ScenarioService } from '../../core/services/scenario.service';
import { Agent, AgentCreate, AgentPersonality } from '../../core/models/agent.model';
import { Scenario } from '../../core/models/scenario.model';
import { EditAgentDialog, EditAgentDialogData, EditAgentDialogResult } from '../../shared/dialogs/edit-agent-dialog/edit-agent-dialog';
import { forkJoin } from 'rxjs';

@Component({
  selector: 'app-user-agents',
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
  templateUrl: './user-agents.html',
  styleUrl: './user-agents.css',
})
export class UserAgents implements OnInit {
  private userContentService = inject(UserContentService);
  private scenarioService = inject(ScenarioService);
  private destroyRef = inject(DestroyRef);
  private fb = inject(FormBuilder);
  private snackBar = inject(MatSnackBar);
  private dialog = inject(MatDialog);

  agents = signal<Agent[]>([]);
  scenarios = signal<Scenario[]>([]);
  personalities = signal<AgentPersonality[]>([]);
  displayedColumns: string[] = ['id', 'name', 'scenario', 'personality', 'voice', 'created_at', 'actions'];
  isLoading = signal(false);
  showCreateForm = signal(false);

  createAgentForm: FormGroup;

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
  }

  ngOnInit() {
    this.loadData();
  }

  loadData() {
    this.isLoading.set(true);
    
    forkJoin({
      agents: this.userContentService.getMyAgents(),
      scenarios: this.scenarioService.getScenarios(),
      personalities: this.userContentService.getMyAgentPersonalities()
    }).subscribe({
      next: (data) => {
        this.agents.set(data.agents);
        this.scenarios.set(data.scenarios);
        this.personalities.set(data.personalities);
        this.isLoading.set(false);
      },
      error: (error) => {
        console.error('Failed to load data', error);
        this.snackBar.open('Failed to load data', 'Close', { duration: 3000 });
        this.isLoading.set(false);
      },
    });
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
      const subscription = this.userContentService.createAgent(agentData).subscribe({
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

  openEditDialog(agent: Agent) {
    const dialogData: EditAgentDialogData = {
      agent,
      scenarios: this.scenarios(),
      personalities: this.personalities(),
    };
    const dialogRef = this.dialog.open(EditAgentDialog, {
      width: '700px',
      maxHeight: '90vh',
      data: dialogData,
    });

    dialogRef.afterClosed().subscribe((result: EditAgentDialogResult | undefined) => {
      if (result) {
        this.saveEdit(agent.id, result);
      }
    });
  }

  private saveEdit(agentId: string, data: EditAgentDialogResult) {
    const subscription = this.userContentService.updateAgent(agentId, data).subscribe({
      next: (updatedAgent) => {
        this.agents.update(agents => 
          agents.map(a => a.id === agentId ? updatedAgent : a)
        );
        this.snackBar.open('Agent updated successfully', 'Close', { duration: 3000 });
      },
      error: (error) => {
        console.error('Failed to update agent', error);
        const errorMessage = error.error?.detail || 'Failed to update agent';
        this.snackBar.open(errorMessage, 'Close', { duration: 5000 });
      },
    });
    this.destroyRef.onDestroy(() => subscription.unsubscribe());
  }

  deleteAgent(agentId: string, name: string) {
    if (confirm(`Are you sure you want to delete agent "${name}"?`)) {
      const subscription = this.userContentService.deleteAgent(agentId).subscribe({
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

