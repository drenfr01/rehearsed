import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatSelectModule } from '@angular/material/select';
import { Feedback, FeedbackType, FeedbackUpdate } from '../../../core/models/feedback.model';

export interface EditFeedbackDialogData {
  feedback: Feedback;
}

export interface EditFeedbackDialogResult extends FeedbackUpdate {}

@Component({
  selector: 'app-edit-feedback-dialog',
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
  templateUrl: './edit-feedback-dialog.html',
})
export class EditFeedbackDialog {
  private fb = inject(FormBuilder);
  private dialogRef = inject(MatDialogRef<EditFeedbackDialog>);
  public data: EditFeedbackDialogData = inject(MAT_DIALOG_DATA);

  feedbackTypes: FeedbackType[] = ['inline', 'summary'];
  editForm: FormGroup;

  constructor() {
    this.editForm = this.fb.group({
      feedback_type: [this.data.feedback.feedback_type, [Validators.required]],
      objective: [this.data.feedback.objective || '', [Validators.required, Validators.minLength(1)]],
      instructions: [this.data.feedback.instructions || '', [Validators.required, Validators.minLength(1)]],
      constraints: [this.data.feedback.constraints || '', [Validators.required, Validators.minLength(1)]],
      context: [this.data.feedback.context || '', [Validators.required, Validators.minLength(1)]],
      output_format: [this.data.feedback.output_format || ''],
    });
  }

  onCancel(): void {
    this.dialogRef.close();
  }

  onSave(): void {
    if (this.editForm.valid) {
      const result: EditFeedbackDialogResult = this.editForm.value;
      this.dialogRef.close(result);
    }
  }

  getFeedbackTypeLabel(type: FeedbackType): string {
    return type === 'inline' ? 'Inline Feedback' : 'Summary Feedback';
  }
}

