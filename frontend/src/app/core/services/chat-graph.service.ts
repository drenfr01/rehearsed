import { inject,  Injectable, signal, effect } from '@angular/core';
import { Message, SummaryFeedbackResponse, FeedbackStatus, FeedbackResponse } from '../models/chat-graph.model';
import { HttpClient } from '@angular/common/http';
import { EMPTY, Observable, catchError, filter, finalize, map, of, switchMap, take, tap, timer } from 'rxjs';
import { ChatRequest, ChatResponse } from '../models/chat-graph.model';
import { environment } from '../../../environments/environment';

type TtsStatus = 'pending' | 'ready' | 'failed';
interface TtsAudioResponse {
  status: TtsStatus;
  audio_base64?: string;
}

interface StreamEvent {
  content: string;
  done: boolean;
  student_name?: string;
  audio_id?: string;
  feedback_request_id?: string;
  interrupt_value?: string;
  interrupt_value_type?: string;
}

@Injectable({
  providedIn: 'root',
})
export class ChatGraphService {
  private httpClient = inject(HttpClient);
  private readonly GRAPH_MESSAGES_KEY = 'chat_graph_messages';
  private readonly INLINE_FEEDBACK_KEY = 'chat_inline_feedback';
  
  private graphMessages = signal<Message[]>(this.loadGraphMessagesFromStorage());
  private ttsStatusById = signal<Map<string, TtsStatus>>(new Map());

  private interruptionContent = signal<string>('')
  private interruptionType = signal<string>('')
  private summaryFeedback = signal<SummaryFeedbackResponse | string>('')
  // TODO: make this not an array? 
  private inlineFeedback = signal<string[]>(this.loadInlineFeedbackFromStorage());
  private feedbackStatus = signal<FeedbackStatus | null>(null);
  private studentResponses = signal<ChatResponse['student_responses']>([]);
  private transcribedText = signal<string>('');

  loadedSummaryFeedback = this.summaryFeedback.asReadonly();
  loadedStudentResponses = this.studentResponses.asReadonly();
  loadedTranscribedText = this.transcribedText.asReadonly();
  loadedTtsStatusById = this.ttsStatusById.asReadonly();
  loadedFeedbackStatus = this.feedbackStatus.asReadonly();

  constructor() {
    // Effect to persist graphMessages to localStorage
    effect(() => {
      const messages = this.graphMessages();
      localStorage.setItem(this.GRAPH_MESSAGES_KEY, JSON.stringify(messages));
    });

    // Effect to persist inlineFeedback to localStorage
    effect(() => {
      const feedback = this.inlineFeedback();
      localStorage.setItem(this.INLINE_FEEDBACK_KEY, JSON.stringify(feedback));
    });
  }

  private loadGraphMessagesFromStorage(): Message[] {
    try {
      const stored = localStorage.getItem(this.GRAPH_MESSAGES_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch (error) {
      console.error('Error loading graph messages from localStorage:', error);
      return [];
    }
  }

  private loadInlineFeedbackFromStorage(): string[] {
    try {
      const stored = localStorage.getItem(this.INLINE_FEEDBACK_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch (error) {
      console.error('Error loading inline feedback from localStorage:', error);
      return [];
    }
  }

  loadedGraphMessages = this.graphMessages.asReadonly();
  loadedInterruptionContent = this.interruptionContent.asReadonly();
  loadedInterruptionType = this.interruptionType.asReadonly();
  loadedInlineFeedback = this.inlineFeedback.asReadonly();

  private getTtsAudio(audioId: string): Observable<TtsAudioResponse> {
    return this.httpClient.get<TtsAudioResponse>(`${environment.baseUrl}/api/v1/tts/${audioId}`);
  }

  private patchMessageAudioBase64(audioId: string, audioBase64: string) {
    const messages = this.graphMessages();
    const updated = messages.map(m => (
      m.audio_id === audioId
        ? { ...m, audio_base64: audioBase64 }
        : m
    ));
    this.graphMessages.set(updated);
  }

  getTtsStatus(audioId: string | undefined): TtsStatus | undefined {
    if (!audioId) return undefined;
    return this.ttsStatusById().get(audioId);
  }

  private setTtsStatus(audioId: string, status: TtsStatus) {
    const next = new Map(this.ttsStatusById());
    next.set(audioId, status);
    this.ttsStatusById.set(next);
  }

  /** Ensure audio is fetched and attached to the matching message(s). */
  ensureTtsAudio(audioId: string): Observable<string> {
    if (!audioId) return EMPTY;

    const existing = this.graphMessages().find(m => m.audio_id === audioId && !!m.audio_base64)?.audio_base64;
    // Uses of in RxJS to emit an observable value that emits the existing audio base64 (if present) 
    if (existing) return of(existing);

    // Poll until ready (short, bounded) so audio becomes available quickly without blocking chat.
    // While polling, mark status pending. If we time out or error, mark failed (enables retry UX).
    this.setTtsStatus(audioId, 'pending');
    let hasAudio = false;

    // Poll every 750ms for up to 20 attempts (1.5s total timeout)
    // Note: we filter the objects to only get the ones that are ready and have audio base64
    // !!r.audio_base64 is a trick to convert the string to a boolean (first ! converts to boolean, second ! negates it)
    // so it's true if the string is not empty, false if it is empty
    return timer(0, 750).pipe(
      take(20),
      switchMap(() => this.getTtsAudio(audioId)),
      filter(r => r.status === 'ready' && !!r.audio_base64),
      map(r => r.audio_base64!),
      take(1),
      tap((audioBase64) => {
        hasAudio = true;
        this.setTtsStatus(audioId, 'ready');
        this.patchMessageAudioBase64(audioId, audioBase64);
      }),
      catchError((err) => {
        console.warn('Failed to fetch TTS audio:', err);
        return EMPTY;
      }),
      finalize(() => {
        if (!hasAudio) {
          this.setTtsStatus(audioId, 'failed');
        }
      }),
    );
  }

  private getFeedback(feedbackId: string): Observable<FeedbackResponse> {
    return this.httpClient.get<FeedbackResponse>(`${environment.baseUrl}/api/v1/chatbot/feedback/${feedbackId}`);
  }

  /** Poll for async inline feedback and update the signal when ready. */
  ensureInlineFeedback(feedbackId: string): Observable<string[]> {
    if (!feedbackId) return EMPTY;

    console.log('Starting feedback polling for:', feedbackId);
    
    // Poll until ready
    this.feedbackStatus.set('pending');
    let hasFeedback = false;
    let pollCount = 0;

    // Poll every 1s for up to 30 attempts (30s total timeout for feedback generation)
    return timer(0, 1000).pipe(
      take(30),
      switchMap(() => {
        pollCount++;
        console.log(`Feedback poll #${pollCount} for ${feedbackId}`);
        return this.getFeedback(feedbackId);
      }),
      tap(r => console.log('Feedback poll response:', r)),
      filter(r => r.status === 'ready' && r.feedback.length > 0),
      map(r => r.feedback),
      take(1),
      tap((feedback) => {
        console.log('Feedback ready, setting:', feedback);
        hasFeedback = true;
        this.feedbackStatus.set('ready');
        this.inlineFeedback.set(feedback);
      }),
      catchError((err) => {
        console.warn('Failed to fetch inline feedback:', err);
        return EMPTY;
      }),
      finalize(() => {
        console.log('Feedback polling finalized, hasFeedback:', hasFeedback);
        if (!hasFeedback) {
          this.feedbackStatus.set('failed');
        }
      }),
    );
  }

  resetGraphMessages() {
    this.graphMessages.set([]);
    this.inlineFeedback.set([]);
    localStorage.removeItem(this.GRAPH_MESSAGES_KEY);
    localStorage.removeItem(this.INLINE_FEEDBACK_KEY);
  }

  /**
   * Send a chat request and stream the student response token-by-token via SSE.
   *
   * A placeholder assistant message is inserted into `graphMessages` immediately
   * so the UI can show a typing indicator.  Each incoming token appends to its
   * `content`.  The final SSE event (done=true) patches in the student name,
   * audio_id, and kicks off feedback polling and TTS prefetch.
   */
  sendStreamingRequest(chatRequest: ChatRequest, initialGraphRequest: boolean): Observable<void> {
    const isAudioMessage = !!chatRequest.audio_base64;

    if (!initialGraphRequest) {
      const humanMessage: Message = {
        role: 'user',
        content: chatRequest.resumption_text || (isAudioMessage ? 'Transcribing...' : ''),
      };
      this.graphMessages.set([...this.graphMessages(), humanMessage]);
    } else {
      this.graphMessages.set([...this.graphMessages(), ...chatRequest.messages]);
    }

    this.inlineFeedback.set([]);
    this.feedbackStatus.set('pending');

    return new Observable<void>(observer => {
      const abortController = new AbortController();

      // Read the bearer token the same way the HTTP interceptor does
      const token = localStorage.getItem('token');

      // Insert a streaming placeholder so the UI shows something immediately
      const placeholderIndex = this.graphMessages().length;
      this.graphMessages.set([
        ...this.graphMessages(),
        { role: 'assistant', content: '' },
      ]);

      fetch(`${environment.baseUrl}/api/v1/chatbot/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          Accept: 'text/event-stream',
        },
        body: JSON.stringify(chatRequest),
        signal: abortController.signal,
      })
        .then(async response => {
          if (!response.ok) {
            const errText = await response.text().catch(() => response.statusText);
            throw new Error(errText || `HTTP ${response.status}`);
          }

          const reader = response.body!.getReader();
          const decoder = new TextDecoder();
          let buffer = '';

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            // SSE events are separated by double newlines
            const parts = buffer.split('\n\n');
            buffer = parts.pop() ?? '';

            for (const part of parts) {
              const dataLine = part
                .split('\n')
                .find(l => l.startsWith('data: '));
              if (!dataLine) continue;

              const event: StreamEvent = JSON.parse(dataLine.slice(6));

              if (!event.done) {
                // Append token to the in-progress assistant message
                const msgs = this.graphMessages();
                const updated = [...msgs];
                updated[placeholderIndex] = {
                  ...updated[placeholderIndex],
                  content: updated[placeholderIndex].content + event.content,
                };
                this.graphMessages.set(updated);
              } else {
                // Final event – patch metadata onto the placeholder message
                const msgs = this.graphMessages();
                const updated = [...msgs];
                updated[placeholderIndex] = {
                  ...updated[placeholderIndex],
                  student_name: event.student_name ?? updated[placeholderIndex].student_name,
                  audio_id: event.audio_id ?? undefined,
                };
                this.graphMessages.set(updated);

                this.interruptionContent.set(event.interrupt_value ?? '');
                this.interruptionType.set(event.interrupt_value_type ?? '');

                // Update transcribed text for audio messages
                if (isAudioMessage && event.content) {
                  const latestMsgs = this.graphMessages();
                  const lastUserIdx = latestMsgs.map(m => m.role).lastIndexOf('user');
                  if (lastUserIdx !== -1) {
                    const withTranscription = [...latestMsgs];
                    withTranscription[lastUserIdx] = {
                      ...withTranscription[lastUserIdx],
                      content: event.content,
                    };
                    this.graphMessages.set(withTranscription);
                  }
                  this.transcribedText.set(event.content);
                }

                // Kick off async feedback polling
                if (event.feedback_request_id) {
                  this.feedbackStatus.set('pending');
                  this.ensureInlineFeedback(event.feedback_request_id).subscribe();
                } else {
                  this.feedbackStatus.set(null);
                }

                // Prefetch TTS audio
                if (event.audio_id) {
                  this.ensureTtsAudio(event.audio_id).subscribe();
                }
              }
            }
          }

          observer.complete();
        })
        .catch(err => {
          if (err.name !== 'AbortError') {
            // Remove the placeholder on error so the UI doesn't show an empty bubble
            const msgs = this.graphMessages();
            this.graphMessages.set(msgs.filter((_, i) => i !== placeholderIndex));
            observer.error(err);
          }
        });

      return () => abortController.abort();
    });
  }

  sendGraphRequest (chatRequest: ChatRequest, initialGraphRequest: boolean): Observable<ChatResponse> {
    // If this is the initial graph request, we need to add the human message to the graph messages
    // otherwise we will build a new resumption message 
    // For audio messages, we'll add a placeholder that gets updated when transcription returns
    const isAudioMessage = !!chatRequest.audio_base64;
    
    if (!initialGraphRequest) {
      const humanMessage: Message = {
        role: 'user',
        content: chatRequest.resumption_text || (isAudioMessage ? 'Transcribing...' : '')
      }
      this.graphMessages.set([...this.graphMessages(), humanMessage]);
    } else {
      this.graphMessages.set([...this.graphMessages(), ...chatRequest.messages]);
    }

    // Immediately show feedback as loading when user sends a message
    // This provides instant visual feedback before the response returns
    this.inlineFeedback.set([]);
    this.feedbackStatus.set('pending');

    return this.httpClient.post<ChatResponse>(`${environment.baseUrl}/api/v1/chatbot/chat`, chatRequest).
    pipe(
      tap((response: ChatResponse) => {
        console.log('Response: ', response);
        console.log('inline_feedback:', response.inline_feedback, 'length:', response.inline_feedback?.length);
        console.log('feedback_request_id:', response.feedback_request_id);
        
        // Inline feedback is now async - set from response if available, or poll
        if (response.inline_feedback && response.inline_feedback.length > 0) {
          console.log('Branch: inline_feedback has content');
          this.inlineFeedback.set(response.inline_feedback);
          this.feedbackStatus.set('ready');
        } else if (response.feedback_request_id) {
          console.log('Branch: starting async feedback polling');
          // Clear previous feedback and start async polling for new feedback
          this.inlineFeedback.set([]);
          this.feedbackStatus.set('pending');
          this.ensureInlineFeedback(response.feedback_request_id).subscribe();
        } else {
          console.log('Branch: no feedback handling (no inline_feedback and no feedback_request_id)');
        }
        this.summaryFeedback.set(response.summary_feedback);
        this.studentResponses.set(response.student_responses);
        this.transcribedText.set(response.transcribed_text || '');
        
        // If this was an audio message, update the user message with the transcribed text
        if (isAudioMessage && response.transcribed_text) {
          const messages = this.graphMessages();
          // Find the last user message and update its content
          const lastUserIndex = messages.map(m => m.role).lastIndexOf('user');
          if (lastUserIndex !== -1) {
            const updatedMessages = [...messages];
            updatedMessages[lastUserIndex] = {
              ...updatedMessages[lastUserIndex],
              content: response.transcribed_text
            };
            this.graphMessages.set(updatedMessages);
          }
        }
        
        if (response.interrupt_task && response.student_responses?.length > 0) {
          // Always use the last (most recent) student response since student_responses is cumulative
          const studentResponse = response.student_responses[response.student_responses.length - 1];
          const responseMessage: Message = {
            role: 'assistant',
            content: response.interrupt_value,
            student_name: studentResponse.student_details.name,
            audio_base64: studentResponse.audio_base64 || undefined,
            audio_id: studentResponse.audio_id || undefined,
          }
          this.interruptionContent.set(response.interrupt_value);
          this.interruptionType.set(response.interrupt_value_type);
          this.graphMessages.set([...this.graphMessages(), responseMessage]);

          // Start background prefetch so audio becomes available ASAP (lazy, but prewarmed).
          if (responseMessage.audio_id && !responseMessage.audio_base64) {
            this.ensureTtsAudio(responseMessage.audio_id).subscribe();
          }
        } else if (response.interrupt_task) {
          // Handle case where there's an interrupt but no student responses
          const responseMessage: Message = {
            role: 'assistant',
            content: response.interrupt_value,
          }
          this.interruptionContent.set(response.interrupt_value);
          this.interruptionType.set(response.interrupt_value_type);
          this.graphMessages.set([...this.graphMessages(), responseMessage]);
        }
      })
    );
  }
}
