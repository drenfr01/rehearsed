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

  loadedSummaryFeedback = this.summaryFeedback.asReadonly();

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
    if (!initialGraphRequest) {
      const humanMessage: Message = {
        role: 'user',
        content: chatRequest.resumption_text
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
        
        if (response.interrupt_task) {
          const responseMessage: Message = {
            role: 'assistant',
            content: response.interrupt_value,
            student_number: response.answering_student
          }
          this.interruptionContent.set(response.interrupt_value);
          this.interruptionType.set(response.interrupt_value_type);
          this.graphMessages.set([...this.graphMessages(), responseMessage]);
        }
      })
    );
  }
}
