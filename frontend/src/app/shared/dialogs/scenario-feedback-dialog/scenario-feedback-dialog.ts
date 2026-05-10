import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { Router } from '@angular/router';
import { ScenarioFeedback } from '../../../features/scenario-feedback/scenario-feedback';
import { ChatOrchestrator } from '../../../core/services/chat-orchestrator.service';
import { MessageStore } from '../../../core/services/message-store.service';
import { InlineFeedbackService } from '../../../core/services/inline-feedback.service';
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
  private chatOrchestrator = inject(ChatOrchestrator);
  private messageStore = inject(MessageStore);
  private feedbackService = inject(InlineFeedbackService);

  protected feedbackData: SummaryFeedbackResponse | string | null = null;

  async onDownloadSession() {
    const summary = this.feedbackData ?? this.chatOrchestrator.summaryFeedback();
    await downloadFeedbackAsPdf({
      summaryFeedback: summary || null,
      transcript: this.messageStore.all(),
      inlineFeedback: this.feedbackService.history(),
    });
  }

  onNewSession() {
    this.chatOrchestrator.resetSession();
    this.dialogRef.close();
    this.router.navigate(['/app/scenario-selection']);
  }

  onReturnHome() {
    this.chatOrchestrator.resetSession();
    this.dialogRef.close();
    this.router.navigate(['/app']);
  }
}
