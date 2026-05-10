import { computed, inject, Injectable, signal, DestroyRef } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { rxResource } from '@angular/core/rxjs-interop';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { of, timer, switchMap, filter, take, tap, catchError, EMPTY, finalize } from 'rxjs';
import { FeedbackStatus, FeedbackResponse, InlineFeedbackEntry } from '../models/chat-graph.model';
import { environment } from '../../../environments/environment';

interface SessionFeedbackEntryResponse {
  turn_id: string;
  feedback: string[];
  status: string;
  created_at: string;
}

interface SessionFeedbackResponse {
  feedback_entries: SessionFeedbackEntryResponse[];
}

@Injectable({ providedIn: 'root' })
export class InlineFeedbackService {
  private http = inject(HttpClient);
  private destroyRef = inject(DestroyRef);

  readonly sessionId = signal<string | null>(null);

  readonly sessionFeedback = rxResource<SessionFeedbackResponse, string | null>({
    params: () => this.sessionId(),
    stream: ({ params: sessionId }) => {
      if (!sessionId) return of({ feedback_entries: [] });
      return this.http.get<SessionFeedbackResponse>(
        `${environment.baseUrl}/api/v1/chatbot/session/${sessionId}/feedback`,
      );
    },
    defaultValue: { feedback_entries: [] },
  });

  private pendingEntries = signal<InlineFeedbackEntry[]>([]);

  readonly history = computed<InlineFeedbackEntry[]>(() => {
    const serverEntries: InlineFeedbackEntry[] =
      this.sessionFeedback.value().feedback_entries.map(e => ({
        turnId: e.turn_id,
        feedback: e.feedback,
        status: e.status as FeedbackStatus,
      }));
    const pending = this.pendingEntries();
    const serverTurnIds = new Set(serverEntries.map(e => e.turnId));
    return [...serverEntries, ...pending.filter(p => !serverTurnIds.has(p.turnId))];
  });

  readonly isAnyPending = computed(() =>
    this.history().some(e => e.status === 'pending'),
  );

  addPending(turnId: string): void {
    this.pendingEntries.update(entries => [
      ...entries,
      { turnId, feedback: [], status: 'pending' as FeedbackStatus },
    ]);
  }

  pollForFeedback(feedbackRequestId: string, turnId: string): void {
    let hasFeedback = false;

    timer(0, 1000).pipe(
      take(30),
      switchMap(() =>
        this.http.get<FeedbackResponse>(
          `${environment.baseUrl}/api/v1/chatbot/feedback/${feedbackRequestId}`,
        ),
      ),
      filter(r => r.status === 'ready' && r.feedback.length > 0),
      take(1),
      tap(r => {
        hasFeedback = true;
        this.updatePendingEntry(turnId, r.feedback, 'ready');
        this.sessionFeedback.reload();
      }),
      catchError(err => {
        console.warn('Failed to fetch inline feedback:', err);
        return EMPTY;
      }),
      finalize(() => {
        if (!hasFeedback) {
          this.updatePendingEntry(turnId, [], 'failed');
        }
      }),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe();
  }

  reset(): void {
    this.pendingEntries.set([]);
    this.sessionId.set(null);
  }

  private updatePendingEntry(turnId: string, feedback: string[], status: FeedbackStatus): void {
    this.pendingEntries.update(entries =>
      entries.map(e =>
        e.turnId === turnId ? { ...e, feedback, status } : e,
      ),
    );
  }
}
