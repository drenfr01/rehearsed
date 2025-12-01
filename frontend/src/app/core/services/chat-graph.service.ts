import { inject,  Injectable, signal, effect } from '@angular/core';
import { Message } from '../models/chat-graph.model';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { ChatRequest, ChatResponse } from '../models/chat-graph.model';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root',
})
export class ChatGraphService {
  private httpClient = inject(HttpClient);
  private readonly GRAPH_MESSAGES_KEY = 'chat_graph_messages';
  private readonly INLINE_FEEDBACK_KEY = 'chat_inline_feedback';
  
  private graphMessages = signal<Message[]>(this.loadGraphMessagesFromStorage());

  private interruptionContent = signal<string>('')
  private interruptionType = signal<string>('')
  private summaryFeedback = signal<string>('')
  // TODO: make this not an array? 
  private inlineFeedback = signal<string[]>(this.loadInlineFeedbackFromStorage());
  private studentResponses = signal<ChatResponse['student_responses']>([]);
  private transcribedText = signal<string>('');

  loadedSummaryFeedback = this.summaryFeedback.asReadonly();
  loadedStudentResponses = this.studentResponses.asReadonly();
  loadedTranscribedText = this.transcribedText.asReadonly();

  constructor() {
    // Effect to persist graphMessages to localStorage
    effect(() => {
      const messages = this.graphMessages();
      localStorage.setItem(this.GRAPH_MESSAGES_KEY, JSON.stringify(messages));
    });

    // Effect to persist inlineFeedback to localStorage
    effect(() => {
      const feedback = this.inlineFeedback();
      localStorage.setItem(this.INLINE_FEEDBACK_KEY, JSON.stringify(feedback));
    });
  }

  private loadGraphMessagesFromStorage(): Message[] {
    try {
      const stored = localStorage.getItem(this.GRAPH_MESSAGES_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch (error) {
      console.error('Error loading graph messages from localStorage:', error);
      return [];
    }
  }

  private loadInlineFeedbackFromStorage(): string[] {
    try {
      const stored = localStorage.getItem(this.INLINE_FEEDBACK_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch (error) {
      console.error('Error loading inline feedback from localStorage:', error);
      return [];
    }
  }

  loadedGraphMessages = this.graphMessages.asReadonly();
  loadedInterruptionContent = this.interruptionContent.asReadonly();
  loadedInterruptionType = this.interruptionType.asReadonly();
  loadedInlineFeedback = this.inlineFeedback.asReadonly();

  resetGraphMessages() {
    this.graphMessages.set([]);
    this.inlineFeedback.set([]);
    localStorage.removeItem(this.GRAPH_MESSAGES_KEY);
    localStorage.removeItem(this.INLINE_FEEDBACK_KEY);
  }

  sendGraphRequest (chatRequest: ChatRequest, initialGraphRequest: boolean): Observable<ChatResponse> {
    // If this is the initial graph request, we need to add the human message to the graph messages
    // otherwise we will build a new resumption message 
    // For audio messages, we'll add a placeholder that gets updated when transcription returns
    const isAudioMessage = !!chatRequest.audio_base64;
    
    if (!initialGraphRequest) {
      const humanMessage: Message = {
        role: 'user',
        content: chatRequest.resumption_text || (isAudioMessage ? 'Transcribing...' : '')
      }
      this.graphMessages.set([...this.graphMessages(), humanMessage]);
    } else {
      this.graphMessages.set([...this.graphMessages(), ...chatRequest.messages]);
    }

    return this.httpClient.post<ChatResponse>(`${environment.baseUrl}/api/v1/chatbot/chat`, chatRequest).
    pipe(
      tap((response: ChatResponse) => {
        console.log('Response: ', response);
        this.inlineFeedback.set(response.inline_feedback);
        this.summaryFeedback.set(response.summary_feedback);
        this.studentResponses.set(response.student_responses);
        this.transcribedText.set(response.transcribed_text || '');
        
        // If this was an audio message, update the user message with the transcribed text
        if (isAudioMessage && response.transcribed_text) {
          const messages = this.graphMessages();
          // Find the last user message and update its content
          const lastUserIndex = messages.map(m => m.role).lastIndexOf('user');
          if (lastUserIndex !== -1) {
            const updatedMessages = [...messages];
            updatedMessages[lastUserIndex] = {
              ...updatedMessages[lastUserIndex],
              content: response.transcribed_text
            };
            this.graphMessages.set(updatedMessages);
          }
        }
        
        if (response.interrupt_task && response.student_responses?.length > 0) {
          // Always use the last (most recent) student response since student_responses is cumulative
          const studentResponse = response.student_responses[response.student_responses.length - 1];
          const responseMessage: Message = {
            role: 'assistant',
            content: response.interrupt_value,
            student_name: studentResponse.student_details.name,
            audio_base64: studentResponse.audio_base64 || undefined
          }
          this.interruptionContent.set(response.interrupt_value);
          this.interruptionType.set(response.interrupt_value_type);
          this.graphMessages.set([...this.graphMessages(), responseMessage]);
        } else if (response.interrupt_task) {
          // Handle case where there's an interrupt but no student responses
          const responseMessage: Message = {
            role: 'assistant',
            content: response.interrupt_value,
          }
          this.interruptionContent.set(response.interrupt_value);
          this.interruptionType.set(response.interrupt_value_type);
          this.graphMessages.set([...this.graphMessages(), responseMessage]);
        }
      })
    );
  }
}
