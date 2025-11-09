import { inject,  Injectable, signal } from '@angular/core';
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
  private graphMessages = signal<Message[]>([]);

  private interruptionContent = signal<string>('')
  private interruptionType = signal<string>('')
  // TODO: make this not an array? 
  private inlineFeedback = signal<string[]>([]);

  loadedGraphMessages = this.graphMessages.asReadonly();
  loadedInterruptionContent = this.interruptionContent.asReadonly();
  loadedInterruptionType = this.interruptionType.asReadonly();
  loadedInlineFeedback = this.inlineFeedback.asReadonly();

  resetGraphMessages() {
    this.graphMessages.set([]);
    this.inlineFeedback.set([]);
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
        if (response.interrupt_task) {
        const responseMessage: Message = {
          role: 'assistant',
          content: response.interrupt_value,
          student_number: response.answering_student
        }
        this.interruptionContent.set(response.interrupt_value);
        this.interruptionType.set(response.interrupt_value_type);
        this.graphMessages.set([...this.graphMessages(), responseMessage]);
        this.inlineFeedback.set(response.inline_feedback);
      }
    })
    );
  }
}
