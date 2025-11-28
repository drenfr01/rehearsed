import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { AgentPersonality } from '../../../core/models/agent.model';

export interface EditPersonalityDialogData {
  personality: AgentPersonality;
}

export interface EditPersonalityDialogResult {
  name: string;
  personality_description: string;
}

@Component({
  selector: 'app-edit-personality-dialog',
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
  ],
  templateUrl: './edit-personality-dialog.html',
})
export class EditPersonalityDialog {
  private fb = inject(FormBuilder);
  private dialogRef = inject(MatDialogRef<EditPersonalityDialog>);
  public data: EditPersonalityDialogData = inject(MAT_DIALOG_DATA);

  editForm: FormGroup;

  constructor() {
    this.editForm = this.fb.group({
      name: [this.data.personality.name, [Validators.required, Validators.minLength(2)]],
      personality_description: [this.data.personality.personality_description, [Validators.required, Validators.minLength(10)]],
    });
  }

  onCancel(): void {
    this.dialogRef.close();
  }

  onSave(): void {
    if (this.editForm.valid) {
      const result: EditPersonalityDialogResult = this.editForm.value;
      this.dialogRef.close(result);
    }
  }
}

