# Rehearsed frontend — design

Angular 20 SPA using **standalone components**, **Angular Material**, and **functional HTTP interceptors**. The app targets the FastAPI backend at `environment.baseUrl` under `/api/v1`.

System context: [../DESIGN.md](../DESIGN.md)  
Backend API patterns: [../backend/DESIGN.md](../backend/DESIGN.md)

---

## Directory layout and responsibilities

| Area | Path | Pattern |
|------|------|---------|
| Shell | `app.ts`, `app.html`, `app.routes.ts`, `app.config.ts` | Root layout (header/footer + `RouterOutlet`); global providers only here. |
| Core | `core/services/`, `core/models/`, `core/components/`, `core/utils/` | Singleton-style **injectable services**, TypeScript **models**, shared **header/footer**, small **utilities** (e.g. PDF, GCS URI). |
| Features | `features/*` | **Route-aligned** smart components: one folder per screen or flow (classroom, scenario-selection, admin-*, user-*, etc.). |
| Shared | `shared/dialogs/`, `shared/loading-spinner/` | **Reusable presentational** pieces (edit dialogs, spinners) imported by features. |

**Convention:** Prefer adding screen-specific logic inside the feature that owns the route. Push cross-cutting API access into `core/services/` when two or more features need the same contract.

---

## Design patterns

### 1. Standalone components and explicit imports

Components and routes use `imports: [...]` in `@Component` / route definitions rather than NgModules for feature bundles. Keeps dependency graphs local and tree-shakable.

### 2. Route tree and authentication guard

- Public routes: `/` (login), `/register`.
- Authenticated subtree: `/app/**` uses `canMatch: [authGuard]` on the parent so all child routes require a valid session.

**Pattern:** Guards own “can activate”; they should not perform heavy data loading—defer to resolvers or component `ngOnInit` / `inject()` + `toSignal` as appropriate for the feature.

### 3. Centralized HTTP + bearer token interceptor

`app.config.ts` registers `provideHttpClient(withInterceptors([bearerTokenInterceptor]))`.

**Pattern — dual token:**

- Most requests use `localStorage.getItem('token')` (session JWT).
- `POST .../api/v1/auth/session` uses `localStorage.getItem('userToken')` so the client can exchange a short-lived or alternate credential for a session token without overwriting the wrong key.

**Rule:** New authenticated endpoints do not manually attach `Authorization`; they rely on the interceptor unless there is an exceptional third-party client.

### 4. Environment-based API base URL

All services build URLs from `environment.baseUrl` + `/api/v1/...`. WebSocket URLs derive from the same base by replacing `http` with `ws` (see `gemini-live.service`).

**Rule:** Never hard-code origin or `/api/v1` in feature templates; always go through `environment` and services.

### 5. Service-per-domain (facade over HttpClient)

Injectable services encapsulate REST shapes and return Observables (or Promises where explicitly chosen, e.g. some live APIs):

| Service | Responsibility |
|---------|----------------|
| `AuthService` | Login, register, session |
| `ScenarioService` | List scenarios, set current, load agents for scenario |
| `ChatGraphService` | Chat turns, feedback fetch, TTS audio fetch |
| `GeminiLiveService` | WebSocket live session + related HTTP |
| `UserContentService` | User-scoped CRUD base path |
| `AdminService` | Admin CRUD + helper fetches (voices, avatars) |
| `LlmConfigService` | LLM models and config for admin app config |

**Pattern:** Services map HTTP errors to user-visible or loggable outcomes at the boundary; components subscribe or use `async` pipe.

### 6. TypeScript models aligned to API

`core/models/*.model.ts` holds interfaces/types shared by services and components (e.g. `Scenario`, `Agent`, chat payloads). When the API changes, update the model and the owning service together.

### 7. Signals where adopted

The root `App` component uses `signal()` for trivial state (e.g. title). New features may use signals or RxJS consistently **within** the feature; avoid mixing both for the same piece of state without a clear bridge (`toSignal` / `toObservable`).

### 8. Shared dialogs

`shared/dialogs/*` provide **edit/create** flows with Material dialogs. Features pass data in via `MAT_DIALOG_DATA` (or project conventions) and close with a result for parent lists to refresh.

### 9. Testing

Specs colocated as `*.spec.ts` use `HttpClientTestingModule` and `HttpTestingController` to assert exact URLs and methods against `environment.baseUrl`. **Pattern:** When adding a service method, add or extend a spec that mocks the HTTP contract.

---

## User journey (routes)

High-level map (all under `/app` except login/register):

1. **Scenario selection → overview → classroom** — primary multi-student simulation.  
2. **Scenario feedback** — post-run feedback presentation.  
3. **One-on-one setup → one-on-one** — narrowed conversation flow.  
4. **My content** — user scenarios, agents, personalities, feedback.  
5. **Admin** — global scenarios, agents, personalities, feedback, app config.

---

## Adding a new feature (checklist)

1. Add route in `app.routes.ts` under the correct parent (`app` + guard vs public).  
2. Add or extend a **core service** if the feature calls a new API surface.  
3. Add **models** for request/response types.  
4. Implement standalone **feature component** under `features/`.  
5. Add **HTTP tests** for new service methods.  
6. Update [../DESIGN.md](../DESIGN.md) only if the **system** boundary changes (new integration, new top-level flow).

---

## Related files (quick reference)

- Routes: `src/app/app.routes.ts`  
- HTTP + interceptor: `src/app/app.config.ts`  
- Auth guard: `src/app/core/services/auth-guard.ts`  
- Environments: `src/environments/environment*.ts`
