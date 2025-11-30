import { Component, DestroyRef, inject, signal, effect, ElementRef, ViewChild } from '@angular/core';
import { Router } from '@angular/router';
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
  private router = inject(Router);

  protected userInput = signal<string>('');
  protected isApproved = signal<boolean>(false);

  // Audio playback state
  protected isPlaying = signal<boolean>(false);
  protected currentAudioUrl = signal<string>('');
  private audioElement: HTMLAudioElement | null = null;

  // Expose readonly signals from the service
  protected messages = this.chatGraphService.loadedGraphMessages;
  protected inlineFeedback = this.chatGraphService.loadedInlineFeedback;
  protected studentResponses = this.chatGraphService.loadedStudentResponses;

  constructor() {
    // Watch for summary feedback and navigate when available
    effect(() => {
      const summaryFeedback = this.chatGraphService.loadedSummaryFeedback();
      if (summaryFeedback && summaryFeedback.trim().length > 0) {
        this.router.navigate(['/app/scenario-feedback']);
      }
    });
    
    // Watch for new student responses and update audio
    effect(() => {
      const responses = this.studentResponses();
      if (responses.length > 0) {
        const latestResponse = responses[responses.length - 1];
        if (latestResponse.audio_base64) {
          this.loadAudio(latestResponse.audio_base64);
        }
      }
    });
    
    // Cleanup audio element on destroy
    this.destroyRef.onDestroy(() => {
      this.cleanupAudio();
    });
  }
  
  private loadAudio(base64Audio: string) {
    // Cleanup previous audio
    this.cleanupAudio();
    
    // Create a blob URL from base64
    const byteCharacters = atob(base64Audio);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    const blob = new Blob([byteArray], { type: 'audio/mp3' });
    const audioUrl = URL.createObjectURL(blob);
    
    this.currentAudioUrl.set(audioUrl);
    this.audioElement = new Audio(audioUrl);
    this.audioElement.onended = () => {
      this.isPlaying.set(false);
    };
  }
  
  private cleanupAudio() {
    if (this.audioElement) {
      this.audioElement.pause();
      this.audioElement = null;
    }
    const currentUrl = this.currentAudioUrl();
    if (currentUrl) {
      URL.revokeObjectURL(currentUrl);
      this.currentAudioUrl.set('');
    }
    this.isPlaying.set(false);
  }
  
  togglePlayPause() {
    if (!this.audioElement) return;
    
    if (this.isPlaying()) {
      this.audioElement.pause();
      this.isPlaying.set(false);
    } else {
      this.audioElement.play();
      this.isPlaying.set(true);
    }
  }
  
  hasAudio(): boolean {
    return this.currentAudioUrl() !== '';
  }

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
