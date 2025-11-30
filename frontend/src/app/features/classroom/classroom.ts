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
  protected audioProgress = signal<number>(0);
  protected audioDuration = signal<number>(0);
  protected audioCurrentTime = signal<number>(0);
  private audioElement: HTMLAudioElement | null = null;
  private isLoadingAudio = false;
  private lastLoadedAudioHash = '';

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
        if (latestResponse.audio_base64 && latestResponse.audio_base64.length > 0) {
          // Create a simple hash to detect duplicate audio data
          const audioHash = latestResponse.audio_base64.substring(0, 100) + latestResponse.audio_base64.length;
          if (audioHash !== this.lastLoadedAudioHash && !this.isLoadingAudio) {
            console.log('Loading audio, base64 length:', latestResponse.audio_base64.length);
            this.lastLoadedAudioHash = audioHash;
            this.loadAudio(latestResponse.audio_base64);
          }
        } else {
          console.log('No audio data in response');
        }
      }
    });
    
    // Cleanup audio element on destroy
    this.destroyRef.onDestroy(() => {
      this.cleanupAudio();
    });
  }
  
  private async loadAudio(base64Audio: string) {
    // Validate input
    if (!base64Audio || base64Audio.trim().length === 0) {
      console.warn('No audio data provided');
      return;
    }
    
    // Prevent concurrent loads
    if (this.isLoadingAudio) {
      console.log('Already loading audio, skipping');
      return;
    }
    
    this.isLoadingAudio = true;
    
    try {
      // Convert base64 to blob using a more reliable method
      const binaryString = atob(base64Audio);
      const len = binaryString.length;
      const bytes = new Uint8Array(len);
      
      // Process in chunks to avoid blocking the main thread
      const chunkSize = 8192;
      for (let offset = 0; offset < len; offset += chunkSize) {
        const end = Math.min(offset + chunkSize, len);
        for (let i = offset; i < end; i++) {
          bytes[i] = binaryString.charCodeAt(i);
        }
        // Yield to main thread every chunk
        if (offset + chunkSize < len) {
          await new Promise(resolve => setTimeout(resolve, 0));
        }
      }
      
      const blob = new Blob([bytes], { type: 'audio/mp3' });
      const newAudioUrl = URL.createObjectURL(blob);
      console.log('Audio blob created, URL:', newAudioUrl, 'Blob size:', blob.size);
      
      // Create the new audio element first
      const newAudioElement = new Audio(newAudioUrl);
      
      // Wait for the audio to be ready before swapping
      await new Promise<void>((resolve, reject) => {
        newAudioElement.oncanplaythrough = () => {
          console.log('Audio ready to play');
          resolve();
        };
        newAudioElement.onerror = (e) => {
          console.error('Audio element error:', e);
          reject(e);
        };
        // Set a timeout in case the events don't fire
        setTimeout(() => resolve(), 5000);
      });
      
      // Now cleanup the old audio and swap in the new one
      this.cleanupAudio();
      
      this.currentAudioUrl.set(newAudioUrl);
      this.audioElement = newAudioElement;
      this.audioDuration.set(newAudioElement.duration || 0);
      this.audioProgress.set(0);
      this.audioCurrentTime.set(0);
      
      this.audioElement.onended = () => {
        this.isPlaying.set(false);
        this.audioProgress.set(0);
        this.audioCurrentTime.set(0);
      };
      
      this.audioElement.ontimeupdate = () => {
        if (this.audioElement && this.audioElement.duration) {
          const progress = (this.audioElement.currentTime / this.audioElement.duration) * 100;
          this.audioProgress.set(progress);
          this.audioCurrentTime.set(this.audioElement.currentTime);
        }
      };
      
      this.audioElement.ondurationchange = () => {
        if (this.audioElement) {
          this.audioDuration.set(this.audioElement.duration);
        }
      };
    } catch (error) {
      console.error('Failed to load audio:', error);
    } finally {
      this.isLoadingAudio = false;
    }
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
    this.audioProgress.set(0);
    this.audioCurrentTime.set(0);
    this.audioDuration.set(0);
  }
  
  seekAudio(event: MouseEvent, progressBarElement: HTMLElement) {
    if (!this.audioElement || !this.audioElement.duration) return;
    
    const rect = progressBarElement.getBoundingClientRect();
    const clickX = event.clientX - rect.left;
    const percentage = clickX / rect.width;
    const newTime = percentage * this.audioElement.duration;
    
    this.audioElement.currentTime = newTime;
    this.audioCurrentTime.set(newTime);
    this.audioProgress.set(percentage * 100);
  }
  
  formatTime(seconds: number): string {
    if (!seconds || isNaN(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
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
