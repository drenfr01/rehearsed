import { Component, inject, computed, input } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { CommonModule } from '@angular/common';
import { ChatGraphService } from '../../core/services/chat-graph.service';
import { marked } from 'marked';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { SummaryFeedbackResponse } from '../../core/models/chat-graph.model';

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

  feedbackData = input<SummaryFeedbackResponse | string | null>(null);

  protected summaryFeedback = computed(() => {
    return this.feedbackData() ?? this.chatGraphService.loadedSummaryFeedback();
  });

  // Check if feedback is structured or a string
  protected isStructuredFeedback = computed<boolean>(() => {
    const feedback = this.summaryFeedback();
    return typeof feedback === 'object' && feedback !== null;
  });

  // Get structured feedback if available
  protected structuredFeedback = computed<SummaryFeedbackResponse | null>(() => {
    const feedback = this.summaryFeedback();
    if (typeof feedback === 'object' && feedback !== null) {
      return feedback as SummaryFeedbackResponse;
    }
    return null;
  });

  // Convert markdown to safe HTML (for string fallback)
  protected summaryFeedbackHtml = computed<SafeHtml>(() => {
    const feedback = this.summaryFeedback();
    if (!feedback) {
      return this.sanitizer.sanitize(1, '<p>No feedback available yet.</p>') || '';
    }
    // If it's a string, parse as markdown
    if (typeof feedback === 'string') {
      const htmlContent = marked.parse(feedback, { async: false }) as string;
      return this.sanitizer.sanitize(1, htmlContent) || '';
    }
    return '';
  });

  // Helper to convert markdown text to safe HTML
  protected markdownToHtml(text: string): SafeHtml {
    if (!text) return '';
    const htmlContent = marked.parse(text, { async: false }) as string;
    return this.sanitizer.sanitize(1, htmlContent) || '';
  }
}
