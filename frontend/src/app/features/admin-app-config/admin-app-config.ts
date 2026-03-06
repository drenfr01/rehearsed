import { Component, DestroyRef, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { LoadingSpinner } from '../../shared/loading-spinner/loading-spinner';
import { LlmConfigService } from '../../core/services/llm-config.service';
import { AgentLlmConfig, AgentType, LlmModel } from '../../core/models/llm-config.model';
import { forkJoin } from 'rxjs';

interface AgentConfigRow {
  agent_type: AgentType;
  label: string;
  description: string;
  selectedModelId: number | null;
}

const AGENT_LABELS: Record<AgentType, { label: string; description: string }> = {
  student_agent: {
    label: 'Student Agent',
    description: 'Generates student responses in the classroom simulation',
  },
  student_choice_agent: {
    label: 'Student Choice Agent',
    description: 'Selects which student responds to the teacher',
  },
  inline_feedback: {
    label: 'Inline Feedback',
    description: 'Provides real-time coaching feedback after each exchange',
  },
  summary_feedback: {
    label: 'Summary Feedback',
    description: 'Generates the end-of-lesson summary report',
  },
};

@Component({
  selector: 'app-admin-app-config',
  imports: [
    CommonModule,
    RouterModule,
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatSelectModule,
    MatSnackBarModule,
    LoadingSpinner,
  ],
  templateUrl: './admin-app-config.html',
  styleUrl: './admin-app-config.css',
})
export class AdminAppConfig implements OnInit {
  private llmConfigService = inject(LlmConfigService);
  private destroyRef = inject(DestroyRef);
  private snackBar = inject(MatSnackBar);

  llmModels = signal<LlmModel[]>([]);
  agentRows = signal<AgentConfigRow[]>([]);
  isLoading = signal(false);
  savingAgentType = signal<AgentType | null>(null);

  ngOnInit() {
    this.loadData();
  }

  loadData() {
    this.isLoading.set(true);
    const subscription = forkJoin({
      models: this.llmConfigService.getLlmModels(),
      configs: this.llmConfigService.getAgentLlmConfigs(),
    }).subscribe({
      next: ({ models, configs }) => {
        this.llmModels.set(models);
        this.buildRows(configs);
        this.isLoading.set(false);
      },
      error: (error) => {
        console.error('Failed to load LLM config', error);
        this.snackBar.open('Failed to load LLM configuration', 'Close', { duration: 3000 });
        this.isLoading.set(false);
      },
    });
    this.destroyRef.onDestroy(() => subscription.unsubscribe());
  }

  private buildRows(configs: AgentLlmConfig[]) {
    const configMap = new Map(configs.map((c) => [c.agent_type, c]));
    const agentTypes: AgentType[] = [
      'student_agent',
      'student_choice_agent',
      'inline_feedback',
      'summary_feedback',
    ];
    this.agentRows.set(
      agentTypes.map((t) => ({
        agent_type: t,
        label: AGENT_LABELS[t].label,
        description: AGENT_LABELS[t].description,
        selectedModelId: configMap.get(t)?.llm_model_id ?? null,
      }))
    );
  }

  onModelChange(row: AgentConfigRow, newModelId: number) {
    this.savingAgentType.set(row.agent_type);
    const subscription = this.llmConfigService
      .updateAgentLlmConfig({ agent_type: row.agent_type, llm_model_id: newModelId })
      .subscribe({
        next: (updated) => {
          row.selectedModelId = updated.llm_model_id;
          this.snackBar.open(
            `${row.label} model updated to ${updated.llm_model_name}`,
            'Close',
            { duration: 3000 }
          );
          this.savingAgentType.set(null);
        },
        error: (error) => {
          console.error('Failed to update LLM config', error);
          const errorMessage = error.error?.detail || 'Failed to update LLM configuration';
          this.snackBar.open(errorMessage, 'Close', { duration: 5000 });
          this.savingAgentType.set(null);
        },
      });
    this.destroyRef.onDestroy(() => subscription.unsubscribe());
  }
}
