# Frontend Testing Coverage

Design document for comprehensive frontend test coverage: unit tests (Vitest), E2E integration tests with mocked backend (Playwright), real E2E smoke tests (Playwright), and GitHub CI/CD integration.

---

## Current State

**Unit tests:** 43 spec files using Angular's `@angular/build:unit-test` runner with Jasmine. Services like `AuthService`, `AdminService`, `ScenarioService`, `UserContentService`, `LlmConfigService`, and `GeminiLiveService` have solid specs. `ChatOrchestrator` and `MessageStore` are tested in `frontend/src/app/core/services/chat-graph.spec.ts`. Most component specs are scaffolded ("should create" only). No specs exist for `InlineFeedbackService` or `TtsAudioService`.

**E2E tests:** None. No Playwright or any E2E framework is installed.

**CI/CD:** Existing `frontend-ci.yml` runs build + unit tests with stale Karma-style flags (`--watch=false --browsers=ChromeHeadless`). No E2E step.

**Backend API:** FastAPI with 10 route groups under `/api/v1/` -- auth, chatbot, gemini-live, scenario, admin, user-content, tts, llm-models, llm-config, avatars.

### Service Inventory

| Service | Spec file | Coverage |
|---------|-----------|----------|
| `AuthService` | `auth.spec.ts` | Solid (login, logout, register, session, JWT parsing, localStorage) |
| `AdminService` | `admin.service.spec.ts` | Solid (all CRUD operations for users, personalities, agents, scenarios, feedback) |
| `ScenarioService` | `scenario.spec.ts` | Solid (getScenarios, setCurrentScenario, agents, localStorage) |
| `UserContentService` | `user-content.service.spec.ts` | Solid (all CRUD + copy operations) |
| `LlmConfigService` | `llm-config.service.spec.ts` | Solid (models, configs, update) |
| `GeminiLiveService` | `gemini-live.service.spec.ts` | Partial (initial state, connect error, disconnect, stopRecording) |
| `ChatOrchestrator` | `chat-graph.spec.ts` | Good (sendChatRequest, resetSession, interrupts, message handling) |
| `MessageStore` | `chat-graph.spec.ts` | Good (append, reset, updateContent, localStorage persistence) |
| `InlineFeedbackService` | **None** | **Missing** |
| `TtsAudioService` | **None** | **Missing** |

### Route / Page Inventory

| Route | Component | Spec depth |
|-------|-----------|------------|
| `/` | `Login` | Good (form validation) |
| `/register` | `Register` | Scaffold only |
| `/app/scenario-selection` | `ScenarioSelection` | Scaffold only |
| `/app/scenario-overview` | `ScenarioOverview` | Scaffold only |
| `/app/classroom` | `Classroom` | Scaffold only |
| `/app/scenario-feedback` | `ScenarioFeedback` | Scaffold only |
| `/app/one-on-one-setup` | `OneOnOneSetup` | Scaffold only |
| `/app/one-on-one` | `OneOnOneConversation` | Minimal (creation + connection state) |
| `/app/my-content` | `UserContent` | Scaffold only |
| `/app/my-content/scenarios` | `UserScenarios` | Scaffold only |
| `/app/my-content/agents` | `UserAgents` | Scaffold only |
| `/app/my-content/personalities` | `UserPersonalities` | Scaffold only |
| `/app/my-content/feedback` | `UserFeedback` | Scaffold only |
| `/app/admin` | `Admin` | Scaffold only |
| `/app/admin/agent-personalities` | `AdminAgentPersonalities` | Scaffold only |
| `/app/admin/agents` | `AdminAgents` | Scaffold only |
| `/app/admin/scenarios` | `AdminScenarios` | Scaffold only |
| `/app/admin/feedback` | `AdminFeedback` | Scaffold only |
| `/app/admin/app-config` | `AdminAppConfig` | Scaffold only |

---

## Phase 1: Migrate Unit Tests to Vitest

Replace Angular's browser-based test runner with Vitest via `@analogjs/vitest-angular`, which provides the Angular TestBed integration needed for component/service tests.

### Steps

1. Install `vitest`, `@analogjs/vitest-angular`, `jsdom` as devDependencies
2. Create `vitest.config.ts` at frontend root
3. Update `tsconfig.spec.json`: replace `"jasmine"` types with `"vitest/globals"`
4. Update `package.json` scripts: `"test": "vitest"`, `"test:ci": "vitest run"`
5. Replace Jasmine matchers in existing specs:
   - `toBeTrue()` --> `toBe(true)`
   - `toBeFalse()` --> `toBe(false)`
   - `spyOn(...).and.returnValue(...)` --> `vi.spyOn(...).mockReturnValue(...)`
6. Remove the `test` architect target from `angular.json` (no longer needed)
7. Verify all 43 existing specs pass under Vitest

### Key Configuration

**`frontend/vitest.config.ts`:**

```typescript
import { defineConfig } from '@analogjs/vitest-angular/setup-zone';

export default defineConfig({
  test: {
    globals: true,
    environment: 'jsdom',
    include: ['src/**/*.spec.ts'],
    setupFiles: ['src/test-setup.ts'],
  },
});
```

**`frontend/tsconfig.spec.json`:**

```json
{
  "extends": "./tsconfig.json",
  "compilerOptions": {
    "outDir": "./out-tsc/spec",
    "types": ["vitest/globals"]
  },
  "include": ["src/**/*.ts"]
}
```

**`frontend/package.json` scripts:**

```json
{
  "test": "vitest",
  "test:ci": "vitest run",
  "test:coverage": "vitest run --coverage"
}
```

---

## Phase 2: Fill Service Unit Test Gaps

Two services have no dedicated spec files. The existing tests are good quality -- new specs match that pattern (TestBed + HttpTestingController).

### 2a. `InlineFeedbackService` spec

**File:** `frontend/src/app/core/services/inline-feedback.service.spec.ts`

| Test case | What it verifies |
|-----------|-----------------|
| `addPending()` adds an entry | Entry appears in `history()` with `status: 'pending'` |
| `history()` merges server + pending | Server entries from `rxResource` are combined with pending, deduped by `turnId` |
| `pollForFeedback()` success | Polls `GET /api/v1/chatbot/feedback/{id}`, updates entry to `ready` with feedback text |
| `pollForFeedback()` failure | After 30 attempts with no ready result, entry marked `failed` |
| `reset()` | Clears `pendingEntries` and sets `sessionId` to `null` |
| `isAnyPending` computed | Returns `true` when any entry has `pending` status, `false` otherwise |

### 2b. `TtsAudioService` spec

**File:** `frontend/src/app/core/services/tts-audio.service.spec.ts`

| Test case | What it verifies |
|-----------|-----------------|
| `getStatus()` unknown ID | Returns `undefined` for IDs not tracked |
| `ensureAudio()` cached | Returns audio from `MessageStore` without HTTP call when already present |
| `ensureAudio()` polls and patches | Polls `GET /api/v1/tts/{id}`, patches audio into `MessageStore` on ready |
| `ensureAudio()` lifecycle | Status transitions: `pending` --> `ready` |
| `ensureAudio()` failure | Sets status to `failed` after exhausting 20 retry attempts |

### 2c. Deepen Shallow Component Specs (Lower Priority)

Most component specs only assert creation. Deeper tests (form validation, signal state, UI rendering) can be added incrementally. The `Login` spec is a good model -- it tests form controls and validation rules. Priority order for deepening:

1. `Login` / `Register` -- form validation, error display, redirect on success
2. `Classroom` -- message sending, student response rendering, feedback display
3. `ScenarioSelection` / `ScenarioOverview` -- data loading, navigation
4. Admin CRUD pages -- table rendering, dialog interaction

---

## Phase 3: Playwright Setup

### Installation

```bash
cd frontend
npm init playwright@latest
```

This installs `@playwright/test` and browser binaries.

### Directory Structure

```
frontend/e2e/
  fixtures/              # Shared test fixtures
    auth.fixture.ts      # Authenticated page fixture
    api-mocks.ts         # Centralized route mocking helpers
  mocks/                 # Mock response data
    auth.mocks.ts
    scenarios.mocks.ts
    chatbot.mocks.ts
    admin.mocks.ts
    user-content.mocks.ts
  mocked/                # E2E tests with mocked backend
    auth.spec.ts
    scenario-selection.spec.ts
    scenario-overview.spec.ts
    classroom.spec.ts
    one-on-one.spec.ts
    feedback.spec.ts
    admin.spec.ts
    user-content.spec.ts
  live/                  # Real E2E tests (require running backend)
    smoke.spec.ts
```

### Playwright Config

**`frontend/playwright.config.ts`:**

```typescript
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  baseURL: 'http://localhost:4200',
  use: {
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'mocked',
      testMatch: 'mocked/**/*.spec.ts',
    },
    {
      name: 'live',
      testMatch: 'live/**/*.spec.ts',
    },
  ],
  webServer: {
    command: 'ng serve',
    url: 'http://localhost:4200',
    reuseExistingServer: true,
  },
});
```

### Auth Fixture

All authenticated routes live under `/app/*` behind `authGuard`. The guard checks for a token in `localStorage`. The auth fixture will:

1. Mock `POST /api/v1/auth/login` and `POST /api/v1/auth/session`
2. Set `localStorage.token` and `localStorage.userToken` with a fake JWT
3. Expose `page` pre-authenticated for use in all guarded-route tests

```typescript
// e2e/fixtures/auth.fixture.ts
import { test as base, Page } from '@playwright/test';
import { MOCK_SESSION_TOKEN, MOCK_USER_TOKEN } from '../mocks/auth.mocks';

export const test = base.extend<{ authedPage: Page }>({
  authedPage: async ({ page }, use) => {
    await page.addInitScript((tokens) => {
      localStorage.setItem('token', tokens.session);
      localStorage.setItem('userToken', tokens.user);
    }, { session: MOCK_SESSION_TOKEN, user: MOCK_USER_TOKEN });
    await use(page);
  },
});
```

### API Mock Layer

A helper that takes a Playwright `page` and registers `page.route()` handlers for each API group. Each mock returns fixture data from the `mocks/` directory. Tests can override specific routes as needed.

```typescript
// e2e/fixtures/api-mocks.ts
export async function mockAllApis(page: Page, overrides?: Partial<ApiMockOverrides>) {
  await mockAuth(page, overrides?.auth);
  await mockScenarios(page, overrides?.scenarios);
  await mockChatbot(page, overrides?.chatbot);
  await mockAdmin(page, overrides?.admin);
  await mockUserContent(page, overrides?.userContent);
  await mockTts(page, overrides?.tts);
  await mockAvatars(page, overrides?.avatars);
  await mockLlm(page, overrides?.llm);
}
```

### Package.json Scripts

```json
{
  "e2e": "npx playwright test --project=mocked",
  "e2e:live": "npx playwright test --project=live",
  "e2e:ui": "npx playwright test --ui"
}
```

---

## Phase 4: E2E Tests with Mocked Backend

All tests use `page.route()` to intercept API calls -- no real backend needed.

### 4a. Auth Flows (`mocked/auth.spec.ts`)

| Test case | Steps |
|-----------|-------|
| Successful login | Fill email + password, submit, verify redirect to `/app/scenario-selection` |
| Login failure | Mock `POST /auth/login` returning 401, verify error message displayed |
| Registration | Fill form, submit, verify success message |
| Logout | Click logout, verify tokens cleared from localStorage, redirect to `/` |
| Session expiry | Mock 401 on any API call, verify redirect to login page |

### 4b. Scenario Selection (`mocked/scenario-selection.spec.ts`)

| Test case | Steps |
|-----------|-------|
| Load scenarios | Mock `GET /scenario/get-all`, verify list renders with scenario names |
| Select scenario | Click a scenario card, verify `POST /scenario/set-current-by-id` called |
| Navigate to overview | After selection, verify redirect to `/app/scenario-overview` |

### 4c. Scenario Overview (`mocked/scenario-overview.spec.ts`)

| Test case | Steps |
|-----------|-------|
| Display details | Verify scenario name, description, and teaching objectives render |
| Show agents | Mock `GET /scenario/{id}/agents`, verify agent list renders |
| Navigate to classroom | Click "Start Classroom", verify navigation to `/app/classroom` |
| Navigate to one-on-one | Click "One-on-One", verify navigation to `/app/one-on-one-setup` |

### 4d. Classroom Simulation (`mocked/classroom.spec.ts`)

| Test case | Steps |
|-----------|-------|
| Send message | Type message, submit, verify `POST /chatbot/chat` called |
| Student response | Mock response with `interrupt_task` + `student_responses`, verify student message renders |
| Inline feedback | Mock `GET /chatbot/feedback/{id}` polling, verify feedback appears inline |
| End session | Trigger end, verify summary feedback dialog displays |

### 4e. One-on-One Conversation (`mocked/one-on-one.spec.ts`)

| Test case | Steps |
|-----------|-------|
| Setup flow | Select scenario + agent on setup page, start conversation |
| Text conversation | Send text message, mock chatbot response, verify message thread |
| Voice mode UI | Verify connection state indicator and recording controls render |

### 4f. Feedback Flows (`mocked/feedback.spec.ts`)

| Test case | Steps |
|-----------|-------|
| Inline feedback | During classroom session, verify feedback appears below user message |
| Summary feedback dialog | After session ends, verify summary dialog with feedback content |
| Scenario feedback page | Navigate to `/app/scenario-feedback`, verify historical feedback loads |
| PDF download | Trigger download, verify download event fires |

### 4g. Admin CRUD (`mocked/admin.spec.ts`)

| Test case | Steps |
|-----------|-------|
| Dashboard loads | Navigate with admin token, verify admin page renders |
| Users: CRUD | List users, create via dialog, edit, delete, approve/reject pending |
| Scenarios: CRUD | List, create, edit, delete scenarios |
| Agents: CRUD | List, create, edit, delete agents |
| Personalities: CRUD | List, create, edit, delete agent personalities |
| Feedback: CRUD | List, create, edit, delete feedback configs |
| LLM config | View models, update agent-to-model assignments |

### 4h. User Content Management (`mocked/user-content.spec.ts`)

| Test case | Steps |
|-----------|-------|
| Dashboard loads | Navigate to `/app/my-content`, verify content hub renders |
| My Scenarios | List, create, edit, delete, copy from global |
| My Agents | List, create, edit, delete, copy from global |
| My Personalities | List, create, edit, delete, copy from global |
| My Feedback | List, create, edit, delete, copy from global |

---

## Phase 5: Real E2E Integration Tests

A small set of smoke tests that hit the actual running backend. These require both `ng serve` and the FastAPI backend running.

### `live/smoke.spec.ts`

| Test case | What it verifies |
|-----------|-----------------|
| Health check | `GET /api/v1/health` returns 200 |
| Login | Login with test credentials, verify session token received |
| Scenario list | Load scenarios, verify non-empty response |
| Scenario overview | Select a scenario, verify overview page renders with real data |
| Classroom interaction | Start a classroom session, send one message, verify a response arrives |

### Configuration

These tests require:
- A `.env.e2e` file (or environment variables) with test user credentials
- The backend running and accessible

```bash
# .env.e2e (not committed -- add to .gitignore)
E2E_TEST_EMAIL=test@example.com
E2E_TEST_PASSWORD=test-password-123
E2E_BASE_URL=http://localhost:8000
```

These tests are separated into the `live` Playwright project so they never run by accident in standard CI.

---

## Phase 6: GitHub CI/CD

### Current State

The existing `.github/workflows/frontend-ci.yml` has a single job that runs build + unit tests with stale Karma-style flags:

```yaml
- name: Run tests
  run: npm run test -- --watch=false --browsers=ChromeHeadless
```

### Updated Workflow: 3 Jobs

```yaml
name: Frontend Pipeline

on:
  push:
    branches: [main]
    paths: ['frontend/**']
  pull_request:
    branches: [main]
    paths: ['frontend/**']
  workflow_dispatch:
    inputs:
      run_live_e2e:
        description: 'Run live E2E tests against staging backend'
        type: boolean
        default: false

jobs:
  unit-tests:
    name: Unit Tests (Vitest)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22.x
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
        working-directory: frontend
      - name: Generate environment file
        working-directory: frontend
        run: |
          cat > src/environments/environment.ts << 'EOF'
          export const environment = {
            baseUrl: '${{ secrets.BASE_URL }}',
            firebaseConfig: {
              apiKey: '${{ secrets.FIREBASE_API_KEY }}',
              authDomain: '${{ secrets.FIREBASE_AUTH_DOMAIN }}',
              projectId: '${{ secrets.FIREBASE_PROJECT_ID }}',
              storageBucket: '${{ secrets.FIREBASE_STORAGE_BUCKET }}',
              messagingSenderId: '${{ secrets.FIREBASE_MESSAGING_SENDER_ID }}',
              appId: '${{ secrets.FIREBASE_APP_ID }}',
              measurementId: '${{ secrets.FIREBASE_MEASUREMENT_ID }}'
            }
          };
          EOF
      - run: npm run test:ci
        working-directory: frontend

  e2e-mocked:
    name: E2E Tests (Mocked Backend)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22.x
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
        working-directory: frontend
      - name: Generate environment file
        working-directory: frontend
        run: |
          cat > src/environments/environment.ts << 'EOF'
          export const environment = {
            baseUrl: '',
            firebaseConfig: {
              apiKey: '', authDomain: '', projectId: '',
              storageBucket: '', messagingSenderId: '',
              appId: '', measurementId: ''
            }
          };
          EOF
      - name: Cache Playwright browsers
        uses: actions/cache@v4
        with:
          path: ~/.cache/ms-playwright
          key: playwright-${{ hashFiles('frontend/package-lock.json') }}
      - name: Install Playwright browsers
        working-directory: frontend
        run: npx playwright install --with-deps chromium
      - run: npx playwright test --project=mocked
        working-directory: frontend
      - name: Upload Playwright report
        if: ${{ !cancelled() }}
        uses: actions/upload-artifact@v4
        with:
          name: playwright-report-mocked
          path: frontend/playwright-report/
          retention-days: 14

  e2e-live:
    name: E2E Tests (Live Backend)
    if: github.event_name == 'workflow_dispatch' && inputs.run_live_e2e
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22.x
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
        working-directory: frontend
      - name: Generate environment file
        working-directory: frontend
        run: |
          cat > src/environments/environment.ts << 'EOF'
          export const environment = {
            baseUrl: '${{ secrets.STAGING_BASE_URL }}',
            firebaseConfig: {
              apiKey: '${{ secrets.FIREBASE_API_KEY }}',
              authDomain: '${{ secrets.FIREBASE_AUTH_DOMAIN }}',
              projectId: '${{ secrets.FIREBASE_PROJECT_ID }}',
              storageBucket: '${{ secrets.FIREBASE_STORAGE_BUCKET }}',
              messagingSenderId: '${{ secrets.FIREBASE_MESSAGING_SENDER_ID }}',
              appId: '${{ secrets.FIREBASE_APP_ID }}',
              measurementId: '${{ secrets.FIREBASE_MEASUREMENT_ID }}'
            }
          };
          EOF
      - name: Cache Playwright browsers
        uses: actions/cache@v4
        with:
          path: ~/.cache/ms-playwright
          key: playwright-${{ hashFiles('frontend/package-lock.json') }}
      - name: Install Playwright browsers
        working-directory: frontend
        run: npx playwright install --with-deps chromium
      - run: npx playwright test --project=live
        working-directory: frontend
        env:
          E2E_TEST_EMAIL: ${{ secrets.E2E_TEST_EMAIL }}
          E2E_TEST_PASSWORD: ${{ secrets.E2E_TEST_PASSWORD }}
      - name: Upload Playwright report
        if: ${{ !cancelled() }}
        uses: actions/upload-artifact@v4
        with:
          name: playwright-report-live
          path: frontend/playwright-report/
          retention-days: 14
```

### Design Decisions

| Decision | Rationale |
|----------|-----------|
| Mocked E2E runs on every PR | No backend needed, safe and fast |
| Live E2E is manual-only (`workflow_dispatch`) | Avoids flaky CI from backend dependencies |
| Chromium-only for Playwright | Saves ~2 min of browser install time vs all 3 engines |
| Browser caching via `actions/cache@v4` | Avoids re-downloading ~150MB of binaries per run |
| Artifact uploads on `!cancelled()` | Reports available for debugging even on failure |
| Empty `baseUrl` for mocked E2E | All API calls intercepted by `page.route()` |
| Unit tests and mocked E2E run in parallel | Faster feedback on PRs |

### Required GitHub Secrets

**Already configured** (used by current workflow):

- `BASE_URL`
- `FIREBASE_API_KEY`, `FIREBASE_AUTH_DOMAIN`, `FIREBASE_PROJECT_ID`, `FIREBASE_STORAGE_BUCKET`, `FIREBASE_MESSAGING_SENDER_ID`, `FIREBASE_APP_ID`, `FIREBASE_MEASUREMENT_ID`

**New secrets needed** (for live E2E only):

- `STAGING_BASE_URL` -- URL of a staging/test backend
- `E2E_TEST_EMAIL` -- test account email
- `E2E_TEST_PASSWORD` -- test account password

---

## Phase 7: OpenAPI Type Generation (HeyAPI)

Replace hand-maintained frontend model files with types generated from the backend's OpenAPI spec using `@hey-api/openapi-ts`. Types only -- no generated HTTP client. Angular services keep their existing `HttpClient`-based implementation and import generated types instead of hand-written interfaces.

### Why

The backend already serves an OpenAPI spec at `/api/v1/openapi.json` (auto-generated from Pydantic schemas). The frontend currently maintains 7 model files (`core/models/*.model.ts`) by hand. These have already drifted from the backend schemas in several places:

- **Duplicate `Agent` / `AgentPersonality` interfaces** — `agent.model.ts` and `chat-graph.model.ts` both define `Agent` with different field sets for the same backend entity.
- **`SessionResponse.token` mismatch** — frontend types the token as `LoginResponse` (requires `is_admin`), but the backend `SessionResponse` returns a `Token` object that has no `is_admin` field.
- **`ChatRequest.resumption_approved`** — exists only on the frontend; the backend schema has no such field.
- **`ChatResponse.interrupt` typed as `object[]`** — total type erasure of the backend's `Interrupt` model.

Auto-generating types eliminates this class of bug and ensures unit test mocks and Playwright fixtures match the real API contract.

### Approach

- **Types only.** Do not generate an HTTP client. The Angular services already wrap `HttpClient` with DI, interceptors, and Observables. A generated fetch-based client would not integrate with that.
- **Offline spec snapshot.** Commit `openapi.json` to the repo so generation works without a running backend. CI validates the snapshot hasn't drifted from the live spec.
- **Keep a `local.model.ts`** for frontend-only types that don't come from the API (e.g. `InlineFeedbackEntry`, `FeedbackStatus`, UI-only view models).

### Steps

1. Install `@hey-api/openapi-ts` as a dev dependency.
2. Create `frontend/openapi-ts.config.ts` — input from committed `openapi.json`, output to `src/app/generated/`, types only (services disabled).
3. Export the backend's current spec to `frontend/openapi.json`.
4. Run generation, verify output covers all route groups (auth, chatbot, scenario, admin, user-content, tts, llm-models, llm-config, avatars, gemini-live).
5. Update Angular services to import from `generated/` instead of `core/models/`.
6. Delete the 7 hand-written model files (keep `local.model.ts` for frontend-only types).
7. Add `"generate:api": "openapi-ts"` script to `package.json`; wire into `prebuild` and `pretest`.
8. Add a CI step that fetches the live spec and diffs against the committed snapshot, failing on drift.
9. Verify build and all existing specs still pass.

### Design Decisions

| Decision | Rationale |
|----------|-----------|
| Types only, no generated client | Preserves Angular `HttpClient` DI, interceptors, and Observable patterns |
| Committed spec snapshot | Generation works offline; CI catches drift |
| Single `generated/` output directory | Clear boundary between auto-generated and hand-written code |
| Frontend-only types stay hand-written | `InlineFeedbackEntry`, `FeedbackStatus`, etc. don't exist in the OpenAPI spec |

---

## Execution Order

| Phase | Depends on | Estimated changes |
|-------|-----------|-------------------|
| Phase 1: Vitest migration | None | ~5 config files, minor edits to 43 spec files |
| Phase 2: Service unit tests | Phase 1 | 2 new spec files |
| Phase 3: Playwright setup | None (parallel with 1-2) | ~8 new files (config + fixtures + mocks) |
| Phase 4: Mocked E2E tests | Phase 3 | ~8 new spec files |
| Phase 5: Live E2E tests | Phase 3 | 1 new spec file |
| Phase 6: CI/CD update | Phase 1 (unit test step), Phase 3 (E2E steps) | 1 workflow file |
| Phase 7: OpenAPI type generation | None (parallel with any phase) | Config + generated output, delete 7 model files, update imports across services/specs |

Phases 1-2, Phase 3, and Phase 7 can all be worked on in parallel since they are independent. Phase 7 will require a follow-up pass on any specs written in Phase 2 to use the generated types. Phase 6 should be updated incrementally: first after Phase 1 completes (to fix the unit test command), then after Phase 3 (to add E2E jobs), then after Phase 7 (to add the spec-drift check).
