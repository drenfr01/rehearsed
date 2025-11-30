import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatSelectModule } from '@angular/material/select';
import { Agent, AgentPersonality, AgentVoice } from '../../../core/models/agent.model';
import { Scenario } from '../../../core/models/scenario.model';
import { AGENT_DISPLAY_COLORS } from '../../../features/user-agents/user-agents';

export interface EditAgentDialogData {
  agent: Agent;
  scenarios: Scenario[];
  personalities: AgentPersonality[];
  voices: AgentVoice[];
}

export interface EditAgentDialogResult {
  name: string;
  scenario_id: number;
  agent_personality_id: number;
  voice: string;
  display_text_color: string;
  objective: string;
  instructions: string;
  constraints: string;
  context: string;
}

@Component({
  selector: 'app-edit-agent-dialog',
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    MatSelectModule,
  ],
  templateUrl: './edit-agent-dialog.html',
})
export class EditAgentDialog {
  private fb = inject(FormBuilder);
  private dialogRef = inject(MatDialogRef<EditAgentDialog>);
  public data: EditAgentDialogData = inject(MAT_DIALOG_DATA);

  editForm: FormGroup;
  displayColors = AGENT_DISPLAY_COLORS;

  constructor() {
    this.editForm = this.fb.group({
      name: [this.data.agent.name, [Validators.required, Validators.minLength(2)]],
      scenario_id: [this.data.agent.scenario_id, [Validators.required]],
      agent_personality_id: [this.data.agent.agent_personality_id, [Validators.required]],
      voice: [this.data.agent.voice || ''],
      display_text_color: [this.data.agent.display_text_color || ''],
      objective: [this.data.agent.objective || ''],
      instructions: [this.data.agent.instructions || ''],
      constraints: [this.data.agent.constraints || ''],
      context: [this.data.agent.context || ''],
    });
  }

  onCancel(): void {
    this.dialogRef.close();
  }

  onSave(): void {
    if (this.editForm.valid) {
      const result: EditAgentDialogResult = this.editForm.value;
      this.dialogRef.close(result);
    }
  }
}

