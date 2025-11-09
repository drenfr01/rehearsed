import { Component, DestroyRef, inject, signal } from '@angular/core';
import { ChatGraphService } from '../../core/services/chat-graph.service';
import { ChatRequest } from '../../core/models/chat-graph.model';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LoadingSpinner } from '../../shared/loading-spinner/loading-spinner';

@Component({
  selector: 'app-classroom',
  imports: [
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatSlideToggleModule,
    CommonModule,
    FormsModule,
    LoadingSpinner,
  ],
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

  // Expose readonly signals from the service
  protected messages = this.chatGraphService.loadedGraphMessages;
  protected inlineFeedback = this.chatGraphService.loadedInlineFeedback;

  onSubmit() {
    this.isLoading.set(true);
    this.error.set('');
    const newChatRequest: ChatRequest = {
      is_resumption: true,
      resumption_text: this.userInput()!,
      resumption_approved: this.isApproved()!,
      messages: [],
    }
    const subscription = this.chatGraphService.sendGraphRequest(newChatRequest, false).subscribe({
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
