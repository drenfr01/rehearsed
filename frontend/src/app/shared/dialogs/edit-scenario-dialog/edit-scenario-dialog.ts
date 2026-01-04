import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { Scenario } from '../../../core/models/scenario.model';

export interface EditScenarioDialogData {
  scenario: Scenario;
}

export interface EditScenarioDialogResult {
  name: string;
  description: string;
  overview: string;
  system_instructions: string;
  initial_prompt: string;
  teaching_objectives: string;
}

@Component({
  selector: 'app-edit-scenario-dialog',
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
  ],
  templateUrl: './edit-scenario-dialog.html',
})
export class EditScenarioDialog {
  private fb = inject(FormBuilder);
  private dialogRef = inject(MatDialogRef<EditScenarioDialog>);
  public data: EditScenarioDialogData = inject(MAT_DIALOG_DATA);

  editForm: FormGroup;

  constructor() {
    this.editForm = this.fb.group({
      name: [this.data.scenario.name, [Validators.required, Validators.minLength(2)]],
      description: [this.data.scenario.description, [Validators.required, Validators.minLength(10)]],
      overview: [this.data.scenario.overview, [Validators.required, Validators.minLength(10)]],
      system_instructions: [this.data.scenario.system_instructions, [Validators.required, Validators.minLength(10)]],
      initial_prompt: [this.data.scenario.initial_prompt, [Validators.required, Validators.minLength(5)]],
      teaching_objectives: [this.data.scenario.teaching_objectives || '', [Validators.required, Validators.minLength(5)]],
    });
  }

  onCancel(): void {
    this.dialogRef.close();
  }

  onSave(): void {
    if (this.editForm.valid) {
      const result: EditScenarioDialogResult = this.editForm.value;
      this.dialogRef.close(result);
    }
  }
}

