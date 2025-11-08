import { inject,  Injectable, signal } from '@angular/core';
import { Message } from '../models/chat-graph.model';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { ChatRequest, ChatResponse } from '../models/chat-graph.model';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root',
})
export class ChatGraph {
  private httpClient = inject(HttpClient);
  private graphMessages = signal<Message[]>([]);

  private interruptionContent = signal<string>('')
  private interruptionType = signal<string>('')

  loadedGraphMessages = this.graphMessages.asReadonly();
  loadedInterruptionContent = this.interruptionContent.asReadonly();
  loadedInterruptionType = this.interruptionType.asReadonly();

  resetGraphMessages() {
    this.graphMessages.set([]);
  }

  sendGraphRequest (chatRequest: ChatRequest): Observable<ChatResponse> {
    let humanText = 'Approved';
    if (chatRequest.resumption_text) {
      humanText = chatRequest.resumption_text;
    }

    const humanMessage: Message = {
      role: 'user',
      content: humanText
    }
    this.graphMessages.set([...this.graphMessages(), humanMessage]);

    return this.httpClient.post<ChatResponse>(`${environment.baseUrl}/api/v1/chatbot/chat`, chatRequest).
    pipe(
      tap((response: ChatResponse) => {
        if (response.interrupt_task) {
        const responseMessage: Message = {
          role: 'assistant',
          content: response.interrupt_task
        }
        this.interruptionContent.set(response.interrupt_value);
        this.interruptionType.set(response.interrupt_value_type);
        this.graphMessages.set([...this.graphMessages(), responseMessage]);
      }
    })
    );
  }
}
