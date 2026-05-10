import { Component, DestroyRef, inject, signal, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { ChatOrchestrator } from '../../core/services/chat-orchestrator.service';
import { MessageStore } from '../../core/services/message-store.service';
import { InlineFeedbackService } from '../../core/services/inline-feedback.service';
import { TtsAudioService } from '../../core/services/tts-audio.service';
import { ScenarioService } from '../../core/services/scenario.service';
import { ChatRequest, InlineFeedbackEntry } from '../../core/models/chat-graph.model';
import { Agent } from '../../core/models/agent.model';
import { firstValueFrom } from 'rxjs';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDialog } from '@angular/material/dialog';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ClassroomStatus } from './classroom-status/classroom-status';
import { ScenarioFeedbackDialog } from '../../shared/dialogs/scenario-feedback-dialog/scenario-feedback-dialog';
import { gcsUriToHttpUrl } from '../../core/utils/gcs-uri.util';

@Component({
  selector: 'app-classroom',
  imports: [
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatSlideToggleModule,
    MatTooltipModule,
    CommonModule,
    FormsModule,
    ClassroomStatus,
  ],
  templateUrl: './classroom.html',
  styleUrl: './classroom.css',
})
export class Classroom implements OnInit {

  protected isLoading = signal(false);
  protected error = signal<string>('');
  private chatOrchestrator = inject(ChatOrchestrator);
  private messageStore = inject(MessageStore);
  private feedbackService = inject(InlineFeedbackService);
  private ttsService = inject(TtsAudioService);
  private scenarioService = inject(ScenarioService);
  private destroyRef = inject(DestroyRef);
  private router = inject(Router);
  private dialog = inject(MatDialog);
  
  private agentColorMap = signal<Map<string, string>>(new Map());
  private agentMap = signal<Map<string, Agent>>(new Map());

  protected userInput = signal<string>('');
  protected isApproved = signal<boolean>(false);

  protected playingMessageIndex = signal<number | null>(null);
  protected isPlaying = signal<boolean>(false);
  private audioElement: HTMLAudioElement | null = null;
  private loadedAudioUrls: Map<number, string> = new Map();

  protected isRecording = signal<boolean>(false);
  private mediaRecorder: MediaRecorder | null = null;
  private recordedChunks: Blob[] = [];
  
  protected recordedAudioUrl = signal<string | null>(null);
  protected isPlayingRecordedAudio = signal<boolean>(false);
  private recordedAudioElement: HTMLAudioElement | null = null;

  protected messages = this.messageStore.all;
  protected feedbackHistory = this.feedbackService.history;
  protected isAnyFeedbackPending = this.feedbackService.isAnyPending;
  protected studentResponses = this.chatOrchestrator.studentResponses;
  protected transcribedText = this.chatOrchestrator.transcribedText;

  constructor() {
    this.destroyRef.onDestroy(() => {
      this.cleanupAllAudio();
      this.cleanupRecordedAudio();
      this.stopRecording();
    });
  }
  
  ngOnInit() {
    this.loadAgentColors();
  }
  
  private loadAgentColors() {
    const currentScenario = this.scenarioService.loadedCurrentScenario();
    if (!currentScenario) return;
    
    const subscription = this.scenarioService.getAgentsByScenario(currentScenario.id).subscribe({
      next: (agents) => {
        const colorMap = new Map<string, string>();
        const agentNameMap = new Map<string, Agent>();
        agents.forEach(agent => {
          if (agent.display_text_color) {
            colorMap.set(agent.name, agent.display_text_color);
          }
          agentNameMap.set(agent.name, agent);
        });
        this.agentColorMap.set(colorMap);
        this.agentMap.set(agentNameMap);
      },
      error: (err) => {
        console.error('Failed to load agent colors:', err);
      },
    });
    
    this.destroyRef.onDestroy(() => subscription.unsubscribe());
  }
  
  getStudentAvatarUrl(studentName: string | undefined): string {
    if (!studentName) return '';
    const agent = this.agentMap().get(studentName);
    if (agent && agent.avatar_gcs_uri) {
      if (agent.avatar_gcs_uri.startsWith('gs://')) {
        return gcsUriToHttpUrl(agent.avatar_gcs_uri);
      }
      return `/${agent.avatar_gcs_uri}`;
    }
    return '';
  }
  
  getAgentColorClass(studentName: string | undefined): string {
    if (!studentName) return 'agent-teal';
    
    const color = this.agentColorMap().get(studentName);
    if (!color) return 'agent-teal';
    
    const colorMap: Record<string, string> = {
      'teal': 'agent-teal',
      'light purple': 'agent-light-purple',
      'dark purple': 'agent-dark-purple',
      'mustard': 'agent-mustard',
      'light blue': 'agent-light-blue',
      'coral': 'agent-coral',
    };
    
    return colorMap[color.toLowerCase()] || 'agent-teal';
  }

  getFeedbackForTurn(turnId: string | undefined): InlineFeedbackEntry | undefined {
    if (!turnId) return undefined;
    return this.feedbackHistory().find(e => e.turnId === turnId);
  }

  protected feedbackExpandedMap = signal<Map<string, boolean>>(new Map());

  isFeedbackExpanded(turnId: string): boolean {
    const map = this.feedbackExpandedMap();
    if (map.has(turnId)) return map.get(turnId)!;
    // Default: the latest pending/ready entry is expanded
    const history = this.feedbackHistory();
    const lastEntry = history[history.length - 1];
    return lastEntry?.turnId === turnId;
  }

  toggleFeedbackExpanded(turnId: string): void {
    const map = new Map(this.feedbackExpandedMap());
    map.set(turnId, !this.isFeedbackExpanded(turnId));
    this.feedbackExpandedMap.set(map);
  }
  
  private async getOrCreateAudioUrl(messageIndex: number, base64Audio: string): Promise<string | null> {
    if (this.loadedAudioUrls.has(messageIndex)) {
      return this.loadedAudioUrls.get(messageIndex)!;
    }
    
    if (!base64Audio || base64Audio.trim().length === 0) {
      return null;
    }
    
    try {
      const binaryString = atob(base64Audio);
      const len = binaryString.length;
      const bytes = new Uint8Array(len);
      
      for (let i = 0; i < len; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }
      
      const blob = new Blob([bytes], { type: 'audio/mp3' });
      const audioUrl = URL.createObjectURL(blob);
      
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
    this.loadedAudioUrls.forEach(url => URL.revokeObjectURL(url));
    this.loadedAudioUrls.clear();
    this.isPlaying.set(false);
    this.playingMessageIndex.set(null);
  }
  
  async togglePlayPauseForMessage(messageIndex: number, audioBase64: string | undefined, audioId: string | undefined) {
    const currentlyPlaying = this.playingMessageIndex();
    
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
    
    if (this.audioElement) {
      this.audioElement.pause();
    }

    let resolvedAudioBase64 = audioBase64;
    if ((!resolvedAudioBase64 || resolvedAudioBase64.trim().length === 0) && audioId) {
      try {
        resolvedAudioBase64 = await firstValueFrom(this.ttsService.ensureAudio(audioId), { defaultValue: '' });
      } catch (error) {
        console.error('Audio not ready or failed to fetch:', error);
        return;
      }
      if (!resolvedAudioBase64) {
        console.warn('Audio still not ready after polling.');
        return;
      }
    }
    
    const audioUrl = await this.getOrCreateAudioUrl(messageIndex, resolvedAudioBase64 || '');
    if (!audioUrl) {
      console.error('Could not load audio for message', messageIndex);
      return;
    }
    
    this.audioElement = new Audio(audioUrl);
    this.audioElement.onended = () => {
      this.isPlaying.set(false);
      this.playingMessageIndex.set(null);
    };
    
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

  getAudioState(message: { audio_base64?: string; audio_id?: string }): 'ready' | 'pending' | 'failed' | 'none' {
    if (message.audio_base64 && message.audio_base64.length > 0) return 'ready';
    if (!message.audio_id) return 'none';
    return this.ttsService.getStatus(message.audio_id) || 'pending';
  }

  isAudioButtonDisabled(message: { audio_base64?: string; audio_id?: string }): boolean {
    return this.getAudioState(message) === 'pending';
  }

  getAudioIcon(messageIndex: number, message: { audio_base64?: string; audio_id?: string }): string {
    const state = this.getAudioState(message);
    if (state === 'pending') return 'hourglass_empty';
    if (state === 'failed') return 'error_outline';
    return this.isMessagePlaying(messageIndex) ? 'pause_circle' : 'play_circle';
  }

  getAudioTooltip(messageIndex: number, message: { audio_base64?: string; audio_id?: string }): string {
    const state = this.getAudioState(message);
    if (state === 'pending') return 'Generating audio...';
    if (state === 'failed') return 'Audio not ready. Click to retry.';
    return this.isMessagePlaying(messageIndex) ? 'Pause' : 'Play';
  }
  
  hasAudioForMessage(message: { audio_base64?: string; audio_id?: string }): boolean {
    return !!(
      (message.audio_base64 && message.audio_base64.length > 0) ||
      (message.audio_id && message.audio_id.length > 0)
    );
  }

  async toggleRecording() {
    if (this.isRecording()) {
      this.stopRecording();
    } else {
      await this.startRecording();
    }
  }

  private async startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') 
        ? 'audio/webm;codecs=opus' 
        : 'audio/webm';
      
      this.mediaRecorder = new MediaRecorder(stream, { mimeType });
      this.recordedChunks = [];

      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          this.recordedChunks.push(event.data);
        }
      };

      this.mediaRecorder.onstop = async () => {
        stream.getTracks().forEach(track => track.stop());
        
        if (this.recordedChunks.length > 0) {
          const audioBlob = new Blob(this.recordedChunks, { type: mimeType });
          
          this.cleanupRecordedAudio();
          const audioUrl = URL.createObjectURL(audioBlob);
          this.recordedAudioUrl.set(audioUrl);
          
          await this.sendAudioMessage(audioBlob);
        }
      };

      this.mediaRecorder.start();
      this.isRecording.set(true);
    } catch (error) {
      console.error('Failed to start recording:', error);
      this.error.set('Could not access microphone. Please check permissions.');
    }
  }

  private stopRecording() {
    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      this.mediaRecorder.stop();
    }
    this.isRecording.set(false);
  }

  private cleanupRecordedAudio() {
    if (this.recordedAudioElement) {
      this.recordedAudioElement.pause();
      this.recordedAudioElement = null;
    }
    const currentUrl = this.recordedAudioUrl();
    if (currentUrl) {
      URL.revokeObjectURL(currentUrl);
    }
    this.recordedAudioUrl.set(null);
    this.isPlayingRecordedAudio.set(false);
  }

  togglePlayRecordedAudio() {
    const audioUrl = this.recordedAudioUrl();
    if (!audioUrl) return;

    if (this.recordedAudioElement && this.isPlayingRecordedAudio()) {
      this.recordedAudioElement.pause();
      this.isPlayingRecordedAudio.set(false);
      return;
    }

    if (!this.recordedAudioElement) {
      this.recordedAudioElement = new Audio(audioUrl);
      this.recordedAudioElement.onended = () => {
        this.isPlayingRecordedAudio.set(false);
      };
    }

    this.recordedAudioElement.play();
    this.isPlayingRecordedAudio.set(true);
  }

  clearRecordedAudio() {
    this.cleanupRecordedAudio();
  }

  private async sendAudioMessage(audioBlob: Blob) {
    const arrayBuffer = await audioBlob.arrayBuffer();
    const uint8Array = new Uint8Array(arrayBuffer);
    let binary = '';
    for (let i = 0; i < uint8Array.length; i++) {
      binary += String.fromCharCode(uint8Array[i]);
    }
    const audioBase64 = btoa(binary);

    this.isLoading.set(true);
    this.error.set('');

    const newChatRequest: ChatRequest = {
      is_resumption: true,
      resumption_text: '',
      resumption_approved: this.isApproved(),
      messages: [],
      audio_base64: audioBase64,
    };

    const subscription = this.chatOrchestrator.sendChatRequest(newChatRequest, false).subscribe({
      error: (error: Error) => {
        this.error.set(error.message);
        this.isLoading.set(false);
      },
      complete: () => {
        this.isLoading.set(false);
      },
    });

    this.destroyRef.onDestroy(() => {
      subscription.unsubscribe();
    });
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
    const subscription = this.chatOrchestrator.sendChatRequest(newChatRequest, false).subscribe({
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

  onEndScenario() {
    this.isLoading.set(true);
    this.error.set('');
    const endScenarioRequest: ChatRequest = {
      is_resumption: true,
      resumption_text: 'goals achieved',
      resumption_approved: this.isApproved()!,
      messages: [],
    }
    const subscription = this.chatOrchestrator.sendChatRequest(endScenarioRequest, false).subscribe({
      next: () => {
        setTimeout(() => {
          const summaryFeedback = this.chatOrchestrator.summaryFeedback();
          if (summaryFeedback) {
            const hasFeedback = typeof summaryFeedback === 'string' 
              ? summaryFeedback.trim().length > 0
              : summaryFeedback !== null;
            if (hasFeedback) {
              this.openFeedbackDialog();
            }
          }
        }, 500);
      },
      error: (error: Error) => {
        this.error.set(error.message);
        this.isLoading.set(false);
      },
      complete: () => {
        this.isLoading.set(false);
      },
    });

    this.destroyRef.onDestroy(() => {
      subscription.unsubscribe();
    });
  }

  private openFeedbackDialog() {
    this.dialog.open(ScenarioFeedbackDialog, {
      width: '90vw',
      maxWidth: '1200px',
      height: '90vh',
      maxHeight: '800px',
      disableClose: false,
      panelClass: 'scenario-feedback-dialog-panel',
    });
  }
}
