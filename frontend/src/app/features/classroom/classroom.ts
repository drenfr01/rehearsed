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

  // Audio playback state - track by message index
  protected playingMessageIndex = signal<number | null>(null);
  protected isPlaying = signal<boolean>(false);
  private audioElement: HTMLAudioElement | null = null;
  private loadedAudioUrls: Map<number, string> = new Map();

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
    
    // Cleanup audio element on destroy
    this.destroyRef.onDestroy(() => {
      this.cleanupAllAudio();
    });
  }
  
  private async getOrCreateAudioUrl(messageIndex: number, base64Audio: string): Promise<string | null> {
    // Check if we already have a URL for this message
    if (this.loadedAudioUrls.has(messageIndex)) {
      return this.loadedAudioUrls.get(messageIndex)!;
    }
    
    if (!base64Audio || base64Audio.trim().length === 0) {
      return null;
    }
    
    try {
      // Convert base64 to blob
      const binaryString = atob(base64Audio);
      const len = binaryString.length;
      const bytes = new Uint8Array(len);
      
      for (let i = 0; i < len; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }
      
      const blob = new Blob([bytes], { type: 'audio/mp3' });
      const audioUrl = URL.createObjectURL(blob);
      
      // Cache the URL
      this.loadedAudioUrls.set(messageIndex, audioUrl);
      return audioUrl;
    } catch (error) {
      console.error('Failed to create audio URL:', error);
      return null;
    }
  }
  
  private cleanupAllAudio() {
    if (this.audioElement) {
      this.audioElement.pause();
      this.audioElement = null;
    }
    // Revoke all cached URLs
    this.loadedAudioUrls.forEach(url => URL.revokeObjectURL(url));
    this.loadedAudioUrls.clear();
    this.isPlaying.set(false);
    this.playingMessageIndex.set(null);
  }
  
  async togglePlayPauseForMessage(messageIndex: number, audioBase64: string) {
    const currentlyPlaying = this.playingMessageIndex();
    
    // If clicking on the same message that's playing, toggle pause/play
    if (currentlyPlaying === messageIndex && this.audioElement) {
      if (this.isPlaying()) {
        this.audioElement.pause();
        this.isPlaying.set(false);
      } else {
        this.audioElement.play();
        this.isPlaying.set(true);
      }
      return;
    }
    
    // Stop any currently playing audio
    if (this.audioElement) {
      this.audioElement.pause();
    }
    
    // Get or create the audio URL for this message
    const audioUrl = await this.getOrCreateAudioUrl(messageIndex, audioBase64);
    if (!audioUrl) {
      console.error('Could not load audio for message', messageIndex);
      return;
    }
    
    // Create new audio element
    this.audioElement = new Audio(audioUrl);
    this.audioElement.onended = () => {
      this.isPlaying.set(false);
      this.playingMessageIndex.set(null);
    };
    
    // Play the audio
    try {
      await this.audioElement.play();
      this.isPlaying.set(true);
      this.playingMessageIndex.set(messageIndex);
    } catch (error) {
      console.error('Failed to play audio:', error);
      this.isPlaying.set(false);
      this.playingMessageIndex.set(null);
    }
  }
  
  isMessagePlaying(messageIndex: number): boolean {
    return this.playingMessageIndex() === messageIndex && this.isPlaying();
  }
  
  hasAudioForMessage(message: { audio_base64?: string }): boolean {
    return !!(message.audio_base64 && message.audio_base64.length > 0);
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

