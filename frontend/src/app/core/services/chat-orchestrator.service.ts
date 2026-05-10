import { inject, Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import {
  ChatRequest,
  ChatResponse,
  Message,
  SummaryFeedbackResponse,
} from '../models/chat-graph.model';
import { MessageStore } from './message-store.service';
import { InlineFeedbackService } from './inline-feedback.service';
import { TtsAudioService } from './tts-audio.service';
import { environment } from '../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class ChatOrchestrator {
  private http = inject(HttpClient);
  private messageStore = inject(MessageStore);
  private feedbackService = inject(InlineFeedbackService);
  private ttsService = inject(TtsAudioService);

  readonly summaryFeedback = signal<SummaryFeedbackResponse | string>('');
  readonly interruptionContent = signal<string>('');
  readonly interruptionType = signal<string>('');
  readonly studentResponses = signal<ChatResponse['student_responses']>([]);
  readonly transcribedText = signal<string>('');

  sendChatRequest(
    chatRequest: ChatRequest,
    isInitial: boolean,
  ): Observable<ChatResponse> {
    const turnId = crypto.randomUUID();
    const isAudioMessage = !!chatRequest.audio_base64;

    if (!isInitial) {
      const humanMessage: Message = {
        role: 'user',
        content: chatRequest.resumption_text || (isAudioMessage ? 'Transcribing...' : ''),
        turnId,
      };
      this.messageStore.appendUser(humanMessage);
    } else {
      const messagesWithTurnId = chatRequest.messages.map(m => ({ ...m, turnId }));
      this.messageStore.appendAll(messagesWithTurnId);
    }

    this.feedbackService.addPending(turnId);

    const requestWithTurnId = { ...chatRequest, turn_id: turnId };

    return this.http
      .post<ChatResponse>(`${environment.baseUrl}/api/v1/chatbot/chat`, requestWithTurnId)
      .pipe(
        tap(response => {
          if (response.inline_feedback && response.inline_feedback.length > 0) {
            // Sync inline feedback is rare but still supported
            this.feedbackService.pollForFeedback('', turnId);
          } else if (response.feedback_request_id) {
            this.feedbackService.pollForFeedback(response.feedback_request_id, turnId);
          }

          this.summaryFeedback.set(response.summary_feedback);
          this.studentResponses.set(response.student_responses);
          this.transcribedText.set(response.transcribed_text || '');

          if (isAudioMessage && response.transcribed_text) {
            this.messageStore.updateContent(turnId, response.transcribed_text);
          }

          if (response.interrupt_task && response.student_responses?.length > 0) {
            const studentResponse =
              response.student_responses[response.student_responses.length - 1];
            const responseMessage: Message = {
              role: 'assistant',
              content: response.interrupt_value,
              student_name: studentResponse.student_details.name,
              audio_base64: studentResponse.audio_base64 || undefined,
              audio_id: studentResponse.audio_id || undefined,
            };
            this.interruptionContent.set(response.interrupt_value);
            this.interruptionType.set(response.interrupt_value_type);
            this.messageStore.appendAssistant(responseMessage);

            if (responseMessage.audio_id && !responseMessage.audio_base64) {
              this.ttsService.ensureAudio(responseMessage.audio_id).subscribe();
            }
          } else if (response.interrupt_task) {
            const responseMessage: Message = {
              role: 'assistant',
              content: response.interrupt_value,
            };
            this.interruptionContent.set(response.interrupt_value);
            this.interruptionType.set(response.interrupt_value_type);
            this.messageStore.appendAssistant(responseMessage);
          }
        }),
      );
  }

  resetSession(): void {
    this.messageStore.reset();
    this.feedbackService.reset();
    this.summaryFeedback.set('');
    this.interruptionContent.set('');
    this.interruptionType.set('');
    this.studentResponses.set([]);
    this.transcribedText.set('');
  }
}
