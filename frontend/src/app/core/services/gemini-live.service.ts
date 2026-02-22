import { Injectable, signal } from '@angular/core';
import { environment } from '../../../environments/environment';

export interface TranscriptEntry {
  role: 'user' | 'agent';
  text: string;
  timestamp: Date;
}

type ConnectionState = 'disconnected' | 'connecting' | 'connected' | 'error';

@Injectable({
  providedIn: 'root',
})
export class GeminiLiveService {
  private ws: WebSocket | null = null;
  private audioContext: AudioContext | null = null;
  private mediaStream: MediaStream | null = null;
  private audioWorkletNode: AudioWorkletNode | null = null;
  private sourceNode: MediaStreamAudioSourceNode | null = null;

  private playbackCtx: AudioContext | null = null;
  private nextPlaybackTime = 0;

  private readonly SAMPLE_RATE_INPUT = 16000;
  private readonly SAMPLE_RATE_OUTPUT = 24000;
  private readonly NATIVE_SAMPLE_RATE = 48000;

  readonly connectionState = signal<ConnectionState>('disconnected');
  readonly transcript = signal<TranscriptEntry[]>([]);
  readonly isRecording = signal(false);
  readonly error = signal<string>('');

  private currentUserUtterance = '';
  private currentAgentUtterance = '';

  async connect(scenarioId: number, agentId: string): Promise<void> {
    this.connectionState.set('connecting');
    this.error.set('');
    this.transcript.set([]);

    const token = localStorage.getItem('token');
    if (!token) {
      this.error.set('Not authenticated');
      this.connectionState.set('error');
      return;
    }

    const wsBase = environment.baseUrl.replace(/^http/, 'ws');
    const wsUrl = `${wsBase}/api/v1/gemini-live/ws?token=${encodeURIComponent(token)}`;

    return new Promise<void>((resolve, reject) => {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        this.ws!.send(JSON.stringify({
          type: 'setup',
          scenario_id: scenarioId,
          agent_id: agentId,
        }));
      };

      this.ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        this.handleServerMessage(msg, resolve);
      };

      this.ws.onerror = () => {
        this.error.set('WebSocket connection failed');
        this.connectionState.set('error');
        reject(new Error('WebSocket connection failed'));
      };

      this.ws.onclose = () => {
        this.stopRecording();
        this.connectionState.set('disconnected');
      };
    });
  }

  private handleServerMessage(msg: any, setupResolve?: (value: void) => void) {
    switch (msg.type) {
      case 'setup_complete':
        this.connectionState.set('connected');
        setupResolve?.();
        break;

      case 'audio':
        this.enqueueAudioPlayback(msg.data);
        break;

      case 'transcript_user':
        this.currentUserUtterance += msg.text;
        this.flushUserUtterance();
        break;

      case 'transcript_agent':
        this.currentAgentUtterance += msg.text;
        this.flushAgentUtterance();
        break;

      case 'turn_complete':
        this.flushAgentUtterance();
        this.currentAgentUtterance = '';
        this.currentUserUtterance = '';
        break;

      case 'error':
        this.error.set(msg.message);
        break;
    }
  }

  private flushUserUtterance() {
    const text = this.currentUserUtterance.trim();
    if (!text) return;

    const entries = this.transcript();
    const last = entries[entries.length - 1];
    if (last && last.role === 'user') {
      this.transcript.set([
        ...entries.slice(0, -1),
        { ...last, text },
      ]);
    } else {
      this.appendTranscript('user', text);
    }
  }

  private flushAgentUtterance() {
    const text = this.currentAgentUtterance.trim();
    if (!text) return;

    const entries = this.transcript();
    const last = entries[entries.length - 1];
    if (last && last.role === 'agent') {
      this.transcript.set([
        ...entries.slice(0, -1),
        { ...last, text },
      ]);
    } else {
      this.appendTranscript('agent', text);
    }
  }

  private appendTranscript(role: 'user' | 'agent', text: string) {
    this.transcript.set([
      ...this.transcript(),
      { role, text, timestamp: new Date() },
    ]);
  }

  async startRecording(): Promise<void> {
    if (this.isRecording()) return;

    try {
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });

      this.audioContext = new AudioContext({ sampleRate: this.NATIVE_SAMPLE_RATE });
      const nativeSampleRate = this.audioContext.sampleRate;
      console.log(`[GeminiLive] AudioContext sample rate: ${nativeSampleRate}, target: ${this.SAMPLE_RATE_INPUT}`);

      this.sourceNode = this.audioContext.createMediaStreamSource(this.mediaStream);

      await this.audioContext.audioWorklet.addModule(
        this.createAudioWorkletUrl()
      );

      this.audioWorkletNode = new AudioWorkletNode(this.audioContext, 'pcm-processor', {
        processorOptions: {
          nativeSampleRate,
          targetSampleRate: this.SAMPLE_RATE_INPUT,
        },
      });
      this.audioWorkletNode.port.onmessage = (event: MessageEvent) => {
        if (this.ws?.readyState === WebSocket.OPEN) {
          const pcmData: Float32Array = event.data;
          const int16 = this.float32ToInt16(pcmData);
          const b64 = this.arrayBufferToBase64(int16.buffer as ArrayBuffer);
          this.ws.send(JSON.stringify({ type: 'audio', data: b64 }));
        }
      };

      this.sourceNode.connect(this.audioWorkletNode);
      this.audioWorkletNode.connect(this.audioContext.destination);

      this.currentUserUtterance = '';
      this.isRecording.set(true);
    } catch (err) {
      this.error.set('Microphone access denied');
      throw err;
    }
  }

  stopRecording() {
    if (this.audioWorkletNode) {
      this.audioWorkletNode.disconnect();
      this.audioWorkletNode = null;
    }
    if (this.sourceNode) {
      this.sourceNode.disconnect();
      this.sourceNode = null;
    }
    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach(t => t.stop());
      this.mediaStream = null;
    }
    this.isRecording.set(false);
  }

  sendText(content: string) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'text', content }));
      this.appendTranscript('user', content);
    }
  }

  disconnect() {
    this.stopRecording();
    if (this.ws) {
      try {
        this.ws.send(JSON.stringify({ type: 'end' }));
      } catch {
        // ignore if already closed
      }
      this.ws.close();
      this.ws = null;
    }
    if (this.playbackCtx && this.playbackCtx.state !== 'closed') {
      this.playbackCtx.close();
    }
    this.playbackCtx = null;
    this.nextPlaybackTime = 0;
    this.connectionState.set('disconnected');
  }

  private enqueueAudioPlayback(base64Pcm: string) {
    const bytes = Uint8Array.from(atob(base64Pcm), c => c.charCodeAt(0));
    const int16 = new Int16Array(bytes.buffer);
    const float32 = new Float32Array(int16.length);
    for (let i = 0; i < int16.length; i++) {
      float32[i] = int16[i] / 32768;
    }
    this.scheduleAudioChunk(float32);
  }

  private scheduleAudioChunk(samples: Float32Array) {
    if (!this.playbackCtx || this.playbackCtx.state === 'closed') {
      this.playbackCtx = new AudioContext({ sampleRate: this.SAMPLE_RATE_OUTPUT });
      this.nextPlaybackTime = this.playbackCtx.currentTime;
    }

    const ctx = this.playbackCtx;
    const buffer = ctx.createBuffer(1, samples.length, this.SAMPLE_RATE_OUTPUT);
    buffer.getChannelData(0).set(samples);

    const source = ctx.createBufferSource();
    source.buffer = buffer;
    source.connect(ctx.destination);

    const startAt = Math.max(this.nextPlaybackTime, ctx.currentTime);
    source.start(startAt);
    this.nextPlaybackTime = startAt + buffer.duration;
  }

  private float32ToInt16(float32: Float32Array): Int16Array {
    const int16 = new Int16Array(float32.length);
    for (let i = 0; i < float32.length; i++) {
      const s = Math.max(-1, Math.min(1, float32[i]));
      int16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }
    return int16;
  }

  private arrayBufferToBase64(buffer: ArrayBuffer): string {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.length; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
  }

  private createAudioWorkletUrl(): string {
    const code = `
      class PcmProcessor extends AudioWorkletProcessor {
        constructor(options) {
          super();
          const opts = options.processorOptions || {};
          this.nativeRate = opts.nativeSampleRate || 48000;
          this.targetRate = opts.targetSampleRate || 16000;
          this.ratio = this.nativeRate / this.targetRate;

          // Buffer to accumulate resampled output (~100ms chunks at target rate)
          this.bufferSize = Math.floor(this.targetRate * 0.1);
          this.buffer = new Float32Array(this.bufferSize);
          this.bufferOffset = 0;

          // Fractional position tracker for resampling
          this.resamplePos = 0;
        }
        process(inputs) {
          const input = inputs[0];
          if (!input || !input[0]) return true;
          const channel = input[0];

          // Linear-interpolation downsample from nativeRate to targetRate
          for (let i = 0; i < channel.length; i++) {
            this.resamplePos++;
            if (this.resamplePos >= this.ratio) {
              this.resamplePos -= this.ratio;
              this.buffer[this.bufferOffset++] = channel[i];
              if (this.bufferOffset >= this.bufferSize) {
                this.port.postMessage(this.buffer.slice());
                this.bufferOffset = 0;
              }
            }
          }
          return true;
        }
      }
      registerProcessor('pcm-processor', PcmProcessor);
    `;
    const blob = new Blob([code], { type: 'application/javascript' });
    return URL.createObjectURL(blob);
  }
}
