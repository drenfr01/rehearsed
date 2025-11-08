import { Component, DestroyRef, inject, signal } from '@angular/core';
import { ChatGraphService } from '../../core/services/chat-graph.service';
import { ChatRequest } from '../../core/models/chat-graph.model';

@Component({
  selector: 'app-classroom',
  imports: [],
  templateUrl: './classroom.html',
  styleUrl: './classroom.css',
})
export class Classroom {

  protected isLoading = signal(false);
  protected error = signal<string>('');
  private chatGraphService = inject(ChatGraphService);
  private destroyRef = inject(DestroyRef);

  protected userInput = signal<string>('');
  protected isApproved = signal<boolean>(false);

  onSubmit() {
    this.isLoading.set(true);
    this.error.set('');
    const newChatRequest: ChatRequest = {
      is_resumption: true,
      resumption_text: this.userInput()!,
      resumption_approved: this.isApproved()!,
      messages: [],
    }
    const subscription = this.chatGraphService.sendGraphRequest(newChatRequest).subscribe({
      error: (error: Error) => {
        this.error.set(error.message);
        this.isLoading.set(false);
      },
      complete: () => {
        this.isLoading.set(false);
        this.userInput.set('');
      },
    });

    this.destroyRef.onDestroy(() => {
      subscription.unsubscribe();
    });
  }
}
