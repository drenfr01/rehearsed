import { Component, inject, computed } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { CommonModule } from '@angular/common';
import { ChatGraphService } from '../../core/services/chat-graph.service';
import { marked } from 'marked';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

@Component({
  selector: 'app-scenario-feedback',
  imports: [
    MatCardModule,
    CommonModule,
  ],
  templateUrl: './scenario-feedback.html',
  styleUrl: './scenario-feedback.css',
})
export class ScenarioFeedback {
  private chatGraphService = inject(ChatGraphService);
  private sanitizer = inject(DomSanitizer);

  // Get the summary feedback from the service
  protected summaryFeedback = this.chatGraphService.loadedSummaryFeedback;

  // Convert markdown to safe HTML
  protected summaryFeedbackHtml = computed<SafeHtml>(() => {
    const markdownContent = this.summaryFeedback();
    if (!markdownContent) {
      return this.sanitizer.sanitize(1, '<p>No feedback available yet.</p>') || '';
    }
    const htmlContent = marked.parse(markdownContent, { async: false }) as string;
    return this.sanitizer.sanitize(1, htmlContent) || '';
  });
}
