import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { Router } from '@angular/router';
import { ScenarioFeedback } from '../scenario-feedback/scenario-feedback';
import { SummaryFeedbackResponse } from '../../core/models/chat-graph.model';

export interface OneOnOneFeedbackDialogData {
  feedback: SummaryFeedbackResponse | string;
}

@Component({
  selector: 'app-one-on-one-feedback-dialog',
  imports: [
    CommonModule,
    MatDialogModule,
    MatButtonModule,
    MatIconModule,
    ScenarioFeedback,
  ],
  template: `
    <div class="scenario-feedback-dialog">
      <h1 class="dialog-title">Session Summary</h1>

      <div class="dialog-content">
        <app-scenario-feedback [feedbackData]="data.feedback" />
      </div>

      <div class="dialog-actions">
        <button
          mat-raised-button
          color="primary"
          (click)="onNewSession()"
          class="action-button"
        >
          <mat-icon>refresh</mat-icon>
          New Session
        </button>

        <button
          mat-raised-button
          (click)="onReturnHome()"
          class="action-button"
        >
          <mat-icon>home</mat-icon>
          Return to Home Page
        </button>
      </div>
    </div>
  `,
  styleUrl:
    '../../shared/dialogs/scenario-feedback-dialog/scenario-feedback-dialog.css',
})
export class OneOnOneFeedbackDialog {
  private dialogRef = inject(MatDialogRef<OneOnOneFeedbackDialog>);
  private router = inject(Router);
  protected data: OneOnOneFeedbackDialogData = inject(MAT_DIALOG_DATA);

  onNewSession() {
    this.dialogRef.close();
    this.router.navigate(['/app/one-on-one-setup']);
  }

  onReturnHome() {
    this.dialogRef.close();
    this.router.navigate(['/app']);
  }
}
