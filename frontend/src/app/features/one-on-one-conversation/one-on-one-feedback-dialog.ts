import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { Router } from '@angular/router';
import { ScenarioFeedback } from '../scenario-feedback/scenario-feedback';
import { SummaryFeedbackResponse, Message } from '../../core/models/chat-graph.model';
import { downloadFeedbackAsPdf } from '../../core/utils/pdf-download.util';

export interface OneOnOneFeedbackDialogData {
  feedback: SummaryFeedbackResponse | string;
  transcript?: Message[];
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
  templateUrl:
    '../../shared/dialogs/scenario-feedback-dialog/scenario-feedback-dialog.html',
  styleUrl:
    '../../shared/dialogs/scenario-feedback-dialog/scenario-feedback-dialog.css',
})
export class OneOnOneFeedbackDialog {
  private dialogRef = inject(MatDialogRef<OneOnOneFeedbackDialog>);
  private router = inject(Router);
  private data: OneOnOneFeedbackDialogData = inject(MAT_DIALOG_DATA);

  protected feedbackData: SummaryFeedbackResponse | string | null = this.data.feedback;

  async onDownloadSession() {
    await downloadFeedbackAsPdf({
      summaryFeedback: this.feedbackData,
      transcript: this.data.transcript,
    });
  }

  onNewSession() {
    this.dialogRef.close();
    this.router.navigate(['/app/one-on-one-setup']);
  }

  onReturnHome() {
    this.dialogRef.close();
    this.router.navigate(['/app']);
  }
}
