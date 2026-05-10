# Feedback Improvements

Design document for planned feedback features and fixes.

---

## 1. Persistent Turn-by-Turn Inline Feedback

**Goal:** Inline feedback accumulates throughout the simulation instead of being replaced each turn. Users can scroll back and review all feedback received while still in the session.

### Current Behavior

- `ChatGraphService.sendGraphRequest()` clears `inlineFeedback` signal on every new message
- Only the most recent turn's feedback is ever visible
- Previous feedback is lost from both the UI and localStorage

### Desired Behavior

- Each turn's inline feedback is preserved in an ordered history
- Feedback appears inline in the chat thread directly below the user message it corresponds to
- The latest feedback starts **expanded**; older feedback **auto-collapses**
- Pending feedback shows a loading indicator; failed feedback shows a subtle note
- Users can expand/collapse any feedback entry manually

### Architecture

**Scope:** Frontend and backend. The backend persists feedback entries per session; the frontend fetches history on load and polls for the current turn during the session.

#### Backend Changes

The backend already generates unique `feedback_id` per turn, stores them in `FeedbackCache`, and serves them via `GET /chatbot/feedback/{id}`. What's missing is a way to retrieve *all* feedback for a session.

**New table — `session_feedback_entry`:**

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `session_id` | FK → `session.id` | |
| `turn_id` | string | Unique identifier for the user message this feedback corresponds to |
| `feedback_request_id` | string | Maps to `FeedbackCache` key |
| `status` | enum(`pending`, `ready`, `failed`) | Updated when feedback generation completes |
| `feedback` | text[] | Populated when status becomes `ready` |
| `created_at` | timestamp | Ordering key |

**Write path:** `generate_feedback_and_store` already receives the session context. After storing in `FeedbackCache`, also upsert a `session_feedback_entry` row with `status: 'pending'`. When the feedback LLM call completes, update the row to `status: 'ready'` with the feedback text.

**New endpoint — `GET /api/v1/chatbot/session/{session_id}/feedback`:**

Returns all feedback entries for a session, ordered by `created_at`:

```json
{
  "feedback_entries": [
    {
      "turn_id": "abc-123",
      "feedback": ["Good use of wait time..."],
      "status": "ready",
      "created_at": "2026-05-10T18:00:00Z"
    }
  ]
}
```

#### Frontend Data Model

Replace the current flat signals:

```typescript
// CURRENT — only holds latest turn
private inlineFeedback = signal<string[]>([]);
private feedbackStatus = signal<FeedbackStatus | null>(null);
```

With a single history signal keyed by `turnId`:

```typescript
interface InlineFeedbackEntry {
  turnId: string;              // unique ID matching Message.turnId
  feedback: string[];          // feedback text(s)
  status: FeedbackStatus;     // pending / ready / failed
  feedbackRequestId?: string; // for polling reference
}

private inlineFeedbackHistory = signal<InlineFeedbackEntry[]>([]);
```

Each `Message` gains a `turnId: string` field, generated client-side (UUID) when the user sends a message and included in the `ChatRequest`. This is the stable key that links messages to feedback entries across both frontend and backend — not an array index.

#### Subscription Management

`InlineFeedbackService` (see item 3 — service decomposition) injects `DestroyRef` and uses `takeUntilDestroyed` to scope all polling subscriptions. Each call to `pollForFeedback()` is scoped so that the service does not accumulate zombie subscriptions across turns.

```typescript
private destroyRef = inject(DestroyRef);

pollForFeedback(feedbackRequestId: string, turnId: string): void {
  timer(0, 1000).pipe(
    take(30),
    switchMap(() => this.http.get<FeedbackResponse>(...)),
    filter(r => r.status === 'ready' && r.feedback.length > 0),
    take(1),
    tap(() => this.sessionFeedback.reload()),
    takeUntilDestroyed(this.destroyRef),
  ).subscribe();
}
```

#### Accumulation Flow

1. **User sends message:** Generate a `turnId` (UUID). Append `InlineFeedbackEntry { turnId, status: 'pending' }` to the history signal. Include `turnId` in the `ChatRequest`.
2. **Backend processes the request:** Creates a `session_feedback_entry` row with `turn_id` and `status: 'pending'`, fires off feedback generation.
3. **`ChatResponse` returns** with `feedback_request_id`: Update the entry matching `turnId` with the request ID and begin polling via `ensureInlineFeedback()`.
4. **Polling completes:** Update entry to `status: 'ready'` with feedback text. All other entries are untouched.
5. **Page load / refresh:** Call `GET /api/v1/chatbot/session/{session_id}/feedback` and hydrate `inlineFeedbackHistory` from the response. No localStorage recovery logic needed.

#### UI Rendering

The classroom component renders `graphMessages()` in order. For each user message with `turnId`:

- Look up `inlineFeedbackHistory` for an entry with matching `turnId`
- If found, render a collapsible feedback card below that user message
- Latest feedback starts expanded; older entries auto-collapse
- Pending: skeleton/loading indicator
- Failed: subtle "feedback unavailable" note

```
[User message (turn 0, turnId: "abc")]
  [Feedback card (collapsed) ▸ ]
[Student response (turn 0)]
[User message (turn 1, turnId: "def")]
  [Feedback card (collapsed) ▸ ]
[Student response (turn 1)]
[User message (turn 2, turnId: "ghi")]
  [Feedback card (expanded, loading...) ▾ ]
```

#### Persistence

- **Server is the source of truth.** No localStorage for inline feedback.
- On page load, `GET /api/v1/chatbot/session/{session_id}/feedback` hydrates the `inlineFeedbackHistory` signal.
- `resetGraphMessages()` clears the frontend signal. Backend feedback entries remain for historical record / future PDF downloads.
- The `INLINE_FEEDBACK_KEY` localStorage key and its associated read/write logic are removed.

#### Public API (InlineFeedbackService)

- `history` (`Signal<InlineFeedbackEntry[]>`) — combined server + pending entries, replaces the old `loadedInlineFeedback`
- `isAnyPending` (`Signal<boolean>`) — convenience for "is anything currently loading", replaces `loadedFeedbackStatus`
- `sessionFeedback.status()` — `rxResource` status (`'idle' | 'loading' | 'reloading' | 'resolved' | 'error'`) for the bulk session fetch
- `sessionId` signal — set to trigger the `rxResource` fetch on page load; changing it auto-fetches for the new session
- `addPending(turnId)` — optimistic entry for immediate UI feedback
- `pollForFeedback(feedbackRequestId, turnId)` — per-turn polling, reloads `rxResource` on completion

### Bug Fix: Stale Feedback Race Condition

This item also resolves a bug where feedback shows content from a previous turn instead of the current one. The root cause is twofold:

1. **Shared signal:** `ensureInlineFeedback()` polling subscriptions all write to the same flat `inlineFeedback` signal, so whichever finishes last wins, potentially overwriting current feedback with stale content.
2. **No subscription cleanup:** Polling subscriptions are never cancelled when a new turn starts, leading to zombie subscriptions that continue hitting the backend.

The `turnId`-keyed `InlineFeedbackEntry[]` architecture eliminates problem (1) by scoping each subscription's writes to its own entry. Injecting `DestroyRef` and using `takeUntilDestroyed` eliminates problem (2) by ensuring all subscriptions are cleaned up when the service is destroyed.

**Regression test:** Add a spec that simulates two rapid sequential turns where the first turn's feedback resolves after the second turn's feedback. Verify that each turn's entry in `inlineFeedbackHistory` contains the correct feedback for its own `turnId`, not the other's.

### Files Changed

**Backend:**
- `backend/app/models/session_feedback_entry.py` — new `SessionFeedbackEntry` SQLModel
- `backend/app/services/feedback_cache.py` — upsert `session_feedback_entry` row alongside `FeedbackCache` writes
- `backend/app/api/v1/chatbot.py` — new `GET /session/{session_id}/feedback` endpoint
- `backend/app/schemas/graph.py` — add `turn_id` to `ChatRequest` schema, add `SessionFeedbackResponse` schema
- Corresponding test files

**Frontend:**
- `frontend/src/app/core/models/chat-graph.model.ts` — add `turnId` to `Message`, add `InlineFeedbackEntry` interface
- `frontend/src/app/core/services/inline-feedback.service.ts` — new service (see item 3), `rxResource` + polling + history signal
- `frontend/src/app/core/services/chat-orchestrator.service.ts` — updated to delegate feedback to `InlineFeedbackService`
- Classroom simulation component — render per-message feedback cards with collapse/expand, inject `InlineFeedbackService`
- Corresponding spec files

### Files Not Changed

- `feedback.model.ts`, admin/user feedback CRUD components
- `ScenarioFeedback` (summary feedback component)
- Shared dialogs

---

## 2. Enhanced PDF Download with Transcript and Inline Feedback

**Goal:** The "Download Session" PDF includes a fully interleaved conversation transcript (each turn with its inline feedback), followed by the summary feedback — for both the classroom and one-on-one flows.

### Current Behavior

- `downloadFeedbackAsPdf()` accepts only `SummaryFeedbackResponse | string` and renders the 7 summary sections
- No transcript or inline feedback appears in the PDF
- `ScenarioFeedbackDialog` (classroom) injects `ChatGraphService` but only passes summary feedback to the PDF util
- `OneOnOneFeedbackDialog` (one-on-one) receives only summary feedback via `MAT_DIALOG_DATA`

### Desired PDF Layout

```
SESSION REPORT

─── Conversation ───

Teacher:
  "Can someone explain what happens when two lines have the same slope?"

  Coach Feedback:
  "You asked a question that builds on student thinking about the role
   of slope — nice work surfacing that concept."

Student (Maria):
  "If they have the same slope they go in the same direction..."

Teacher:
  "Great observation. What does that mean for the system of equations?"

  Coach Feedback:
  "You connected the student's observation back to the mathematical
   structure — this aligns with subskill 3."

Student (James):
  "It means they're parallel so they never cross?"

...

─── Session Summary ───

Lesson Summary
...
Key Moments
...
(etc.)
```

For one-on-one sessions, the layout is the same but without "Coach Feedback" entries (inline feedback does not exist in the Gemini Live flow).

### Architecture

**Scope:** Frontend-only. The backend already exposes the necessary data via the session feedback endpoint (item 1) and existing signals.

#### Data Model

Expand the PDF utility's input from a single feedback value to a structured payload. Use `Message` directly rather than introducing a redundant `TranscriptEntry` type — `Message` already has `role`, `content`, and `student_name`:

```typescript
interface PdfDownloadData {
  summaryFeedback: SummaryFeedbackResponse | string | null;
  transcript?: Message[];
  inlineFeedback?: InlineFeedbackEntry[];  // from item 1, keyed by turnId
}
```

#### Rendering Logic in `pdf-download.util.ts`

1. **Conversation section:** Iterate through `transcript`. For each message:
   - Render role label ("Teacher" for user, "Student (Name)" for assistant with `student_name`)
   - Render message content (stripped of markdown)
   - If the message is a user message, look up `inlineFeedback` for a matching `turnId` with `status === 'ready'` and render the feedback indented below as "Coach Feedback"
2. **Summary section:** Render the existing `buildSections()` output (unchanged)
3. Page breaks managed by the existing `ensureSpace` helper

#### Data Flow per Dialog

**Classroom — `ScenarioFeedbackDialog`:**
- Injects `MessageStore` for transcript and `InlineFeedbackService` for feedback history (per item 3 decomposition)
- Read `messageStore.all()` as the transcript (`Message[]`)
- Read `feedbackService.history()` (from item 1) as inline feedback
- Read `chatOrchestrator.summaryFeedback()` as summary

**One-on-one — `OneOnOneFeedbackDialog`:**
- Expand `OneOnOneFeedbackDialogData` to include the transcript:

```typescript
// CURRENT
export interface OneOnOneFeedbackDialogData {
  feedback: SummaryFeedbackResponse | string;
}

// NEW
export interface OneOnOneFeedbackDialogData {
  feedback: SummaryFeedbackResponse | string;
  transcript?: Message[];
}
```

- The component that opens this dialog passes `GeminiLiveService.transcript()` mapped to `Message[]`
- No inline feedback in this flow — the PDF renders transcript without coach feedback entries

#### Dependency on Item 1

The inline feedback entries in the PDF come from `InlineFeedbackEntry[]` (item 1), keyed by `turnId`. If this item is implemented before item 1, the classroom PDF can still include the transcript without inline feedback, and inline feedback rendering is added once item 1 lands. The `inlineFeedback` field in `PdfDownloadData` is optional for this reason.

### Files Changed

- `frontend/src/app/core/utils/pdf-download.util.ts` — new `PdfDownloadData` interface, transcript + inline feedback rendering
- `frontend/src/app/shared/dialogs/scenario-feedback-dialog/scenario-feedback-dialog.ts` — pass transcript + inline feedback to PDF util
- `frontend/src/app/features/one-on-one-conversation/one-on-one-feedback-dialog.ts` — expand dialog data, pass transcript to PDF util
- The component that opens the one-on-one feedback dialog — pass `GeminiLiveService.transcript()` in dialog data
- `frontend/src/app/core/utils/pdf-download.util.spec.ts` — tests for transcript and inline feedback rendering in PDF

### Files Not Changed

- All backend files (session feedback endpoint from item 1 is sufficient)
- Admin/user feedback CRUD components
- `ScenarioFeedback` component (summary feedback display — unchanged)
- `ChatOrchestrator` (data already exposed via decomposed services; no new methods needed beyond item 1)

---

## 3. Service Decomposition: ChatGraphService

**Goal:** Break the current `ChatGraphService` god service into focused, single-responsibility services that are independently testable and use Angular 20+ idioms (`rxResource` with `params`/`stream`, `DestroyRef`, signal-based state).

### Current Problem

`ChatGraphService` owns all of the following:

- Message list state + localStorage persistence
- TTS audio polling, status tracking, and message patching
- Inline feedback polling + status
- Summary feedback state
- Student responses state
- Transcription state
- Interruption state
- HTTP communication (`POST /chat`, `GET /feedback/{id}`, `GET /tts/{id}`)
- Response orchestration (the 90-line `sendGraphRequest` tap block that coordinates all of the above)

This makes it difficult to test any single concern in isolation, leads to tangled signal dependencies, and means every consumer (classroom, feedback dialogs, PDF export) imports one massive service even when they only need a slice of its state.

### Proposed Decomposition

```
┌─────────────────────────────────────────────────────────┐
│                   Components                            │
│  Classroom, ScenarioFeedbackDialog, OneOnOneFeedback    │
│                                                         │
│   inject only the services they actually need           │
└────────┬──────────┬──────────────┬──────────────────────┘
         │          │              │
         ▼          ▼              ▼
┌──────────────┐ ┌───────────────┐ ┌───────────────────┐
│ MessageStore │ │ InlineFeedback│ │  TtsAudioService  │
│              │ │   Service     │ │                   │
│ messages     │ │ history       │ │ status tracking   │
│ persistence  │ │ rxResource    │ │ polling           │
│ mutations    │ │ polling       │ │ message patching  │
└──────┬───────┘ └───────┬───────┘ └────────┬──────────┘
       │                 │                   │
       └────────┬────────┴───────────────────┘
                │
                ▼
       ┌─────────────────┐
       │ ChatOrchestrator│
       │                 │
       │ sendChatRequest │
       │ response routing│
       │ session signals │
       └─────────────────┘
```

#### 3a. `MessageStore`

Pure state service — no HTTP, no side effects beyond localStorage.

```typescript
@Injectable({ providedIn: 'root' })
export class MessageStore {
  private readonly STORAGE_KEY = 'chat_graph_messages';

  private messages = signal<Message[]>(this.loadFromStorage());

  readonly all = this.messages.asReadonly();

  constructor() {
    effect(() => {
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(this.messages()));
    });
  }

  appendUser(message: Message): void { ... }
  appendAssistant(message: Message): void { ... }
  updateContent(turnId: string, content: string): void { ... }
  patchAudio(audioId: string, audioBase64: string): void { ... }
  reset(): void { ... }

  private loadFromStorage(): Message[] { ... }
}
```

**Why separate:** Message state is consumed by the classroom, feedback dialogs, and PDF export — none of which need feedback polling or TTS logic. Extracting it means consumers can inject `MessageStore` alone. It's also trivially testable (no HTTP mocking needed).

#### 3b. `InlineFeedbackService`

Owns inline feedback history. Uses `rxResource` for the session-level fetch and manual polling for the current turn.

```typescript
@Injectable({ providedIn: 'root' })
export class InlineFeedbackService {
  private http = inject(HttpClient);
  private destroyRef = inject(DestroyRef);

  /** The active session ID — drives the rxResource. */
  readonly sessionId = signal<string | null>(null);

  /**
   * rxResource: fetches all feedback for the current session.
   * Automatically re-fetches when sessionId changes (switch-map semantics).
   * Provides .value(), .status(), .isLoading(), .error(), .reload() for free.
   */
  readonly sessionFeedback = rxResource<SessionFeedbackResponse, string | null>({
    params: () => this.sessionId(),
    stream: ({ params: sessionId }) => {
      if (!sessionId) return of({ feedback_entries: [] });
      return this.http.get<SessionFeedbackResponse>(
        `${environment.baseUrl}/api/v1/chatbot/session/${sessionId}/feedback`
      );
    },
    defaultValue: { feedback_entries: [] },
  });

  /**
   * Optimistic local entries for the current turn (not yet on the server).
   * Cleared when sessionFeedback.reload() brings them in from the backend.
   */
  private pendingEntries = signal<InlineFeedbackEntry[]>([]);

  /**
   * Combined view: server entries merged with local pending entries.
   * Server entries take precedence (by turnId) when both exist.
   */
  readonly history = computed<InlineFeedbackEntry[]>(() => {
    const server = this.sessionFeedback.value().feedback_entries.map(e => ({
      turnId: e.turn_id,
      feedback: e.feedback,
      status: e.status as FeedbackStatus,
    }));
    const pending = this.pendingEntries();
    const serverTurnIds = new Set(server.map(e => e.turnId));
    return [...server, ...pending.filter(p => !serverTurnIds.has(p.turnId))];
  });

  /** Whether any entry is currently pending. */
  readonly isAnyPending = computed(() =>
    this.history().some(e => e.status === 'pending')
  );

  /** Add optimistic pending entry when user sends a message. */
  addPending(turnId: string): void { ... }

  /**
   * Poll for a single turn's feedback. On completion, reload the
   * rxResource so server becomes the source of truth.
   */
  pollForFeedback(feedbackRequestId: string, turnId: string): void {
    timer(0, 1000).pipe(
      take(30),
      switchMap(() => this.http.get<FeedbackResponse>(...)),
      filter(r => r.status === 'ready' && r.feedback.length > 0),
      take(1),
      tap(() => this.sessionFeedback.reload()),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe();
  }

  reset(): void {
    this.pendingEntries.set([]);
    this.sessionId.set(null);
  }
}
```

**Key design decisions:**

- `rxResource` owns the server state with built-in loading/error/reload lifecycle. No manual status signals needed — `sessionFeedback.status()` gives you `'idle' | 'loading' | 'reloading' | 'resolved' | 'error'` for free.
- `pendingEntries` is the optimistic overlay for the current turn while polling. Once polling completes, `sessionFeedback.reload()` fetches from the server and the `computed` merge drops the local entry in favor of the server's version.
- Changing `sessionId` automatically triggers a fresh fetch (switch-map semantics built into `rxResource`). Navigating to a new session or refreshing the page just requires setting the signal.
- `DestroyRef` + `takeUntilDestroyed` scopes all polling subscriptions.

#### 3c. `TtsAudioService`

Owns TTS polling and status. Delegates message patching to `MessageStore`.

```typescript
@Injectable({ providedIn: 'root' })
export class TtsAudioService {
  private http = inject(HttpClient);
  private destroyRef = inject(DestroyRef);
  private messageStore = inject(MessageStore);

  private statusById = signal<Map<string, TtsStatus>>(new Map());
  readonly allStatuses = this.statusById.asReadonly();

  getStatus(audioId: string | undefined): TtsStatus | undefined { ... }

  /**
   * Poll for TTS audio. On success, patches the audio onto the
   * corresponding message in MessageStore.
   */
  ensureAudio(audioId: string): Observable<string> {
    // ...existing polling logic...
    // On success: this.messageStore.patchAudio(audioId, base64)
    // Scoped with takeUntilDestroyed(this.destroyRef)
  }
}
```

**Why separate:** TTS is a self-contained concern (poll, cache, patch). The classroom component needs `TtsAudioService` for playback controls but doesn't need feedback logic. Feedback dialogs and PDF export never touch TTS at all.

#### 3d. `ChatOrchestrator`

Thin coordinator — makes the HTTP call and routes the response to the appropriate services. Holds only the transient per-response signals that don't warrant their own service (summary, interruptions, student responses, transcription).

```typescript
@Injectable({ providedIn: 'root' })
export class ChatOrchestrator {
  private http = inject(HttpClient);
  private messageStore = inject(MessageStore);
  private feedbackService = inject(InlineFeedbackService);
  private ttsService = inject(TtsAudioService);

  // Transient per-response state
  readonly summaryFeedback = signal<SummaryFeedbackResponse | string>('');
  readonly interruptionContent = signal<string>('');
  readonly interruptionType = signal<string>('');
  readonly studentResponses = signal<ChatResponse['student_responses']>([]);
  readonly transcribedText = signal<string>('');

  sendChatRequest(request: ChatRequest, isInitial: boolean): Observable<ChatResponse> {
    const turnId = crypto.randomUUID();

    // 1. Optimistic message append
    if (!isInitial) {
      this.messageStore.appendUser({ role: 'user', content: ..., turnId });
    }

    // 2. Optimistic feedback pending entry
    this.feedbackService.addPending(turnId);

    // 3. HTTP call
    return this.http.post<ChatResponse>(...).pipe(
      tap(response => {
        // Route feedback
        if (response.feedback_request_id) {
          this.feedbackService.pollForFeedback(response.feedback_request_id, turnId);
        }

        // Route transient state
        this.summaryFeedback.set(response.summary_feedback);
        this.studentResponses.set(response.student_responses);
        this.transcribedText.set(response.transcribed_text || '');

        // Route transcription update
        if (request.audio_base64 && response.transcribed_text) {
          this.messageStore.updateContent(turnId, response.transcribed_text);
        }

        // Route assistant messages + TTS prefetch
        if (response.interrupt_task) {
          const msg = this.buildAssistantMessage(response);
          this.messageStore.appendAssistant(msg);
          if (msg.audio_id) this.ttsService.ensureAudio(msg.audio_id).subscribe();
        }
      }),
    );
  }

  resetSession(): void {
    this.messageStore.reset();
    this.feedbackService.reset();
  }
}
```

**Why this shape:** `sendGraphRequest` was 90 lines of `tap` because it was doing everything. Now each concern is a single method call on a focused service. The orchestrator is easy to read — it's just routing.

### Migration Path

This decomposition can be done incrementally behind the existing `ChatGraphService` API:

1. **Extract `MessageStore`** — move signals and localStorage logic. `ChatGraphService` delegates to it internally. No consumer changes.
2. **Extract `TtsAudioService`** — move TTS polling. `ChatGraphService` delegates. Update `Classroom` to inject `TtsAudioService` directly for status/playback methods.
3. **Extract `InlineFeedbackService`** with `rxResource` — this is the item 1 work, now in its own service from the start.
4. **Rename `ChatGraphService` → `ChatOrchestrator`** — at this point it's just the thin coordinator. Update remaining consumer imports.

Each step is independently shippable and testable. The old `ChatGraphService` public API can be preserved as a facade during migration if needed.

### Consumer Impact

| Consumer | Before | After |
|----------|--------|-------|
| `Classroom` | injects `ChatGraphService` for everything | injects `ChatOrchestrator` (send), `MessageStore` (messages), `InlineFeedbackService` (feedback), `TtsAudioService` (audio) |
| `ScenarioFeedbackDialog` | injects `ChatGraphService` | injects `MessageStore` + `InlineFeedbackService` + reads `summaryFeedback` from `ChatOrchestrator` |
| `OneOnOneFeedbackDialog` | receives data via `MAT_DIALOG_DATA` | unchanged — data still passed in via dialog data |
| `ScenarioFeedback` | reads summary signal | reads from `ChatOrchestrator.summaryFeedback` |

### Files Changed

- `frontend/src/app/core/services/message-store.service.ts` — new
- `frontend/src/app/core/services/inline-feedback.service.ts` — new
- `frontend/src/app/core/services/tts-audio.service.ts` — new
- `frontend/src/app/core/services/chat-graph.service.ts` → renamed to `chat-orchestrator.service.ts`
- `frontend/src/app/features/classroom/classroom.ts` — update injections
- `frontend/src/app/shared/dialogs/scenario-feedback-dialog/scenario-feedback-dialog.ts` — update injections
- `frontend/src/app/features/scenario-feedback/scenario-feedback.ts` — update injections
- `frontend/src/app/features/scenario-overview/scenario-overview.ts` — update injections
- Corresponding spec files

---

## 4. Upgrade to Angular 21

**Goal:** Upgrade from Angular 20.3 to Angular 21 (latest: 21.2.x). Adopt zoneless change detection and migrate the test runner from Karma/Jasmine to Vitest.

### Current State

| Dependency | Current | Target |
|-----------|---------|--------|
| `@angular/core` | `^20.3.0` | `^21.2.0` |
| `@angular/cli` | `^20.3.9` | `^21.2.0` |
| `@angular/build` | `^20.3.9` | `^21.2.0` |
| `@angular/material` | `^20.2.12` | `^21.x` |
| `@angular/cdk` | `^20.2.12` | `^21.x` |
| `typescript` | `~5.9.2` | `~5.9.2` (compatible) |
| `zone.js` | `~0.15.0` | removed from polyfills |
| Test runner | Karma + Jasmine | Vitest |

### Breaking Changes That Affect This Project

**1. Zone.js is no longer included by default**

Angular 21 removes zone.js from new apps. This project currently uses `provideZoneChangeDetection({ eventCoalescing: true })` in `app.config.ts` and includes `zone.js` in the build and test polyfills in `angular.json`.

The `Classroom` component uses `NgZone.run()` in four places — all inside browser API callbacks (`MediaRecorder.onstop`, `MediaRecorder.start` callback, error handler, and `Audio.onended`). With zoneless change detection, signal writes are automatically picked up by Angular's scheduler, so these `NgZone.run()` wrappers become unnecessary and can be removed.

**Migration:**
- Remove `provideZoneChangeDetection()` from `app.config.ts` (the automated migration covers this)
- Add `provideExperimentalZonelessChangeDetection()` or just remove the provider entirely (Angular 21 is zoneless by default)
- Remove `zone.js` from `polyfills` arrays in `angular.json` (both build and test)
- Remove `zone.js` from `package.json` dependencies
- Remove all `NgZone.run()` calls in `Classroom` — signal writes inside callbacks already notify Angular's scheduler without zone.js
- Remove `NgZone` import and injection from `Classroom`

**2. TypeScript 5.9 is the minimum**

Already satisfied — the project is on `~5.9.2`.

**3. Host binding type checking enabled by default**

Already satisfied — `tsconfig.json` already has `"typeCheckHostBindings": true`.

**4. `experimentalDecorators` should be removed**

`tsconfig.json` has `"experimentalDecorators": true`. Angular 21 uses TC39 standard decorators. This flag is no longer needed and may cause issues — remove it.

**5. `moduleId` removed from Component metadata**

Not used in this project — no action needed.

**6. `interpolation` option removed from Components**

Not used in this project — no action needed.

**7. `ApplicationConfig` export removed from `@angular/platform-browser`**

`app.config.ts` imports `ApplicationConfig` from `@angular/core` — already correct.

**8. `lastSuccessfulNavigation` is now a signal**

Verify no code reads `router.lastSuccessfulNavigation` as a property — if so, update to call it as a signal (`router.lastSuccessfulNavigation()`).

### Migrate Test Runner: Karma → Vitest

Angular 21 makes Vitest the stable default. Karma/Jasmine are still supported but Vitest is the recommended path forward.

**Migration steps:**

1. Run the automated migration:
   ```bash
   ng g @schematics/angular:refactor-jasmine-vitest
   ```
   This rewrites `describe`/`it`/`expect` calls and test config automatically.

2. Update `angular.json` — replace the test builder:
   ```json
   // BEFORE
   "test": {
     "builder": "@angular/build:karma",
     "options": {
       "polyfills": ["zone.js", "zone.js/testing"],
       ...
     }
   }

   // AFTER
   "test": {
     "builder": "@angular/build:vitest",
     "options": {
       "tsConfig": "tsconfig.spec.json"
     }
   }
   ```

3. Remove Karma/Jasmine dev dependencies:
   ```
   karma, karma-chrome-launcher, karma-coverage, karma-jasmine, karma-jasmine-html-reporter, jasmine-core, @types/jasmine
   ```

4. Verify all specs pass with `ng test`.

### Execution Order

Run `ng update` which handles most of the mechanical changes:

```bash
ng update @angular/core@21 @angular/cli@21 @angular/material@21
```

Then apply manual changes in this order:

1. **`tsconfig.json`** — remove `experimentalDecorators`
2. **`app.config.ts`** — remove `provideZoneChangeDetection`, remove `zone.js` import if present
3. **`angular.json`** — remove `zone.js` from polyfills (build + test)
4. **`package.json`** — remove `zone.js` dependency
5. **`Classroom`** — remove `NgZone` injection and all `.run()` wrappers
6. **Test migration** — run the Jasmine → Vitest schematic, update `angular.json` test builder, remove Karma deps
7. **Full test run** — `ng test` and `ng build` to verify

### Files Changed

- `frontend/package.json` — version bumps, remove `zone.js`, remove Karma/Jasmine deps
- `frontend/angular.json` — remove zone.js polyfills, switch test builder to Vitest
- `frontend/tsconfig.json` — remove `experimentalDecorators`
- `frontend/src/app/app.config.ts` — remove `provideZoneChangeDetection`
- `frontend/src/app/features/classroom/classroom.ts` — remove `NgZone` usage
- All `*.spec.ts` files — Jasmine → Vitest syntax (automated by schematic)
- `karma.conf.js` (if exists) — deleted

### Files Not Changed

- All backend files
- Component templates and styles (no zone.js-dependent patterns)
- Service logic (signals already work without zone.js)
