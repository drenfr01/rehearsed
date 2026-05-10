import { inject, Injectable, signal, DestroyRef } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { EMPTY, Observable, catchError, filter, finalize, map, of, switchMap, take, tap, timer } from 'rxjs';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { MessageStore } from './message-store.service';
import { environment } from '../../../environments/environment';

export type TtsStatus = 'pending' | 'ready' | 'failed';

interface TtsAudioResponse {
  status: TtsStatus;
  audio_base64?: string;
}

@Injectable({ providedIn: 'root' })
export class TtsAudioService {
  private http = inject(HttpClient);
  private destroyRef = inject(DestroyRef);
  private messageStore = inject(MessageStore);

  private statusById = signal<Map<string, TtsStatus>>(new Map());
  readonly allStatuses = this.statusById.asReadonly();

  getStatus(audioId: string | undefined): TtsStatus | undefined {
    if (!audioId) return undefined;
    return this.statusById().get(audioId);
  }

  private setStatus(audioId: string, status: TtsStatus): void {
    const next = new Map(this.statusById());
    next.set(audioId, status);
    this.statusById.set(next);
  }

  ensureAudio(audioId: string): Observable<string> {
    if (!audioId) return EMPTY;

    const existing = this.messageStore
      .all()
      .find(m => m.audio_id === audioId && !!m.audio_base64)?.audio_base64;
    if (existing) return of(existing);

    this.setStatus(audioId, 'pending');
    let hasAudio = false;

    return timer(0, 750).pipe(
      take(20),
      switchMap(() =>
        this.http.get<TtsAudioResponse>(`${environment.baseUrl}/api/v1/tts/${audioId}`),
      ),
      filter(r => r.status === 'ready' && !!r.audio_base64),
      map(r => r.audio_base64!),
      take(1),
      tap(audioBase64 => {
        hasAudio = true;
        this.setStatus(audioId, 'ready');
        this.messageStore.patchAudio(audioId, audioBase64);
      }),
      catchError(err => {
        console.warn('Failed to fetch TTS audio:', err);
        return EMPTY;
      }),
      finalize(() => {
        if (!hasAudio) this.setStatus(audioId, 'failed');
      }),
      takeUntilDestroyed(this.destroyRef),
    );
  }
}
