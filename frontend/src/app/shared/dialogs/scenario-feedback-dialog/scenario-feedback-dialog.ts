import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { Router } from '@angular/router';
import { ScenarioFeedback } from '../../../features/scenario-feedback/scenario-feedback';
import { ChatGraphService } from '../../../core/services/chat-graph.service';
import { SummaryFeedbackResponse } from '../../../core/models/chat-graph.model';
import { downloadFeedbackAsPdf } from '../../../core/utils/pdf-download.util';

@Component({
  selector: 'app-scenario-feedback-dialog',
  imports: [
    CommonModule,
    MatDialogModule,
    MatButtonModule,
    MatIconModule,
    ScenarioFeedback,
  ],
  templateUrl: './scenario-feedback-dialog.html',
  styleUrl: './scenario-feedback-dialog.css',
})
export class ScenarioFeedbackDialog {
  private dialogRef = inject(MatDialogRef<ScenarioFeedbackDialog>);
  private router = inject(Router);
  private chatGraphService = inject(ChatGraphService);

  protected feedbackData: SummaryFeedbackResponse | string | null = null;

  async onDownloadSession() {
    const data = this.feedbackData ?? this.chatGraphService.loadedSummaryFeedback();
    await downloadFeedbackAsPdf(data, 'session-feedback.pdf');
  }

  onNewSession() {
    this.chatGraphService.resetGraphMessages();
    this.dialogRef.close();
    this.router.navigate(['/app/scenario-selection']);
  }

  onReturnHome() {
    this.chatGraphService.resetGraphMessages();
    this.dialogRef.close();
    this.router.navigate(['/app']);
  }
}
