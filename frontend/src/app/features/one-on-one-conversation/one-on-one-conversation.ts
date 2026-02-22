import { Component, DestroyRef, inject, signal, OnInit, OnDestroy, ElementRef, ViewChild, effect } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { GeminiLiveService, TranscriptEntry } from '../../core/services/gemini-live.service';
import { ScenarioService } from '../../core/services/scenario.service';
import { Agent } from '../../core/models/agent.model';
import { Scenario } from '../../core/models/scenario.model';
import { gcsUriToHttpUrl } from '../../core/utils/gcs-uri.util';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatTooltipModule } from '@angular/material/tooltip';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-one-on-one-conversation',
  imports: [
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatTooltipModule,
    CommonModule,
    FormsModule,
  ],
  templateUrl: './one-on-one-conversation.html',
  styleUrl: './one-on-one-conversation.css',
})
export class OneOnOneConversation implements OnInit, OnDestroy {
  @ViewChild('transcriptContainer') transcriptContainer!: ElementRef;

  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private destroyRef = inject(DestroyRef);
  private geminiLive = inject(GeminiLiveService);
  private scenarioService = inject(ScenarioService);

  protected connectionState = this.geminiLive.connectionState;
  protected transcript = this.geminiLive.transcript;
  protected isRecording = this.geminiLive.isRecording;
  protected error = this.geminiLive.error;

  protected agent = signal<Agent | null>(null);
  protected scenario = signal<Scenario | null>(null);
  protected textInput = signal('');
  protected isConnecting = signal(false);

  private scenarioId: number | null = null;
  private agentId: string | null = null;

  constructor() {
    effect(() => {
      this.transcript();
      this.scrollToBottom();
    });
  }

  ngOnInit() {
    const params = this.route.snapshot.queryParams;
    this.scenarioId = params['scenarioId'] ? Number(params['scenarioId']) : null;
    this.agentId = params['agentId'] || null;

    if (!this.scenarioId || !this.agentId) {
      this.router.navigate(['/app/one-on-one-setup']);
      return;
    }

    this.scenario.set(this.scenarioService.loadedCurrentScenario());
    this.loadAgent();
    this.connectToGemini();
  }

  ngOnDestroy() {
    this.geminiLive.disconnect();
  }

  private loadAgent() {
    if (!this.scenarioId || !this.agentId) return;
    const sub = this.scenarioService.getAgentsByScenario(this.scenarioId).subscribe({
      next: (agents) => {
        const found = agents.find(a => a.id === this.agentId);
        if (found) this.agent.set(found);
      },
    });
    this.destroyRef.onDestroy(() => sub.unsubscribe());
  }

  private async connectToGemini() {
    if (!this.scenarioId || !this.agentId) return;
    this.isConnecting.set(true);
    try {
      await this.geminiLive.connect(this.scenarioId, this.agentId);
    } catch {
      // errors are surfaced via geminiLive.error signal
    } finally {
      this.isConnecting.set(false);
    }
  }

  getAgentAvatarUrl(): string {
    const a = this.agent();
    if (!a?.avatar_gcs_uri) return '';
    if (a.avatar_gcs_uri.startsWith('gs://')) return gcsUriToHttpUrl(a.avatar_gcs_uri);
    return `/${a.avatar_gcs_uri}`;
  }

  toggleMic() {
    if (this.isRecording()) {
      this.geminiLive.stopRecording();
    } else {
      this.geminiLive.startRecording();
    }
  }

  sendText() {
    const text = this.textInput().trim();
    if (!text) return;
    this.geminiLive.sendText(text);
    this.textInput.set('');
  }

  onTextKeydown(event: KeyboardEvent) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendText();
    }
  }

  endConversation() {
    this.geminiLive.disconnect();
    this.router.navigate(['/app/one-on-one-setup']);
  }

  private scrollToBottom() {
    setTimeout(() => {
      const el = this.transcriptContainer?.nativeElement;
      if (el) el.scrollTop = el.scrollHeight;
    }, 50);
  }
}
