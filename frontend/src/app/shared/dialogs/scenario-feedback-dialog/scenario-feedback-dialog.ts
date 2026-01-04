import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { Router } from '@angular/router';
import { ScenarioFeedback } from '../../../features/scenario-feedback/scenario-feedback';
import { ChatGraphService } from '../../../core/services/chat-graph.service';

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

  onDownloadSession() {
    // TODO: Implement download session functionality
    console.log('Download session clicked');
    // This could download the conversation history, feedback, etc.
  }

  onNewSession() {
    // Reset the graph messages and navigate to scenario selection
    this.chatGraphService.resetGraphMessages();
    this.dialogRef.close();
    this.router.navigate(['/app/scenario-selection']);
  }

  onReturnHome() {
    // Reset the graph messages and navigate to home
    this.chatGraphService.resetGraphMessages();
    this.dialogRef.close();
    this.router.navigate(['/app']);
  }
}
