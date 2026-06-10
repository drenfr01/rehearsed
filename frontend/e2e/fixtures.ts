import { Page } from '@playwright/test';
import type {
  ScenarioWithOwnerResponse,
  SessionResponse,
  TokenResponse,
} from '../src/app/core/api';

function base64Url(value: object): string {
  return Buffer.from(JSON.stringify(value)).toString('base64url');
}

/** A structurally valid (but unsigned) JWT so the app can decode its payload. */
export function fakeJwt(payload: Record<string, unknown> = {}): string {
  return `${base64Url({ alg: 'HS256', typ: 'JWT' })}.${base64Url(payload)}.fake-signature`;
}

const expiresAt = new Date(Date.now() + 60 * 60 * 1000).toISOString();

export const mockLoginResponse: TokenResponse = {
  access_token: fakeJwt({ sub: 'teacher@example.com', is_admin: false }),
  token_type: 'bearer',
  expires_at: expiresAt,
  is_admin: false,
};

export const mockSessionResponse: SessionResponse = {
  session_id: 'session-123',
  name: '',
  token: {
    access_token: fakeJwt({ sub: 'teacher@example.com', session_id: 'session-123', is_admin: false }),
    token_type: 'bearer',
    expires_at: expiresAt,
  },
};

export const mockScenarios: ScenarioWithOwnerResponse[] = [
  {
    id: 1,
    name: 'Fractions Lesson',
    description: 'Practice teaching fractions to a 5th grade class',
    overview: 'A classroom of curious students learning fractions',
    system_instructions: '',
    initial_prompt: 'Start the lesson',
    teaching_objectives: 'Teach equivalent fractions',
    created_at: '2024-01-01T00:00:00Z',
    owner_id: null,
    is_global: true,
  },
  {
    id: 2,
    name: 'Reading Comprehension',
    description: 'Guide students through a short story discussion',
    overview: 'Literature discussion practice',
    system_instructions: '',
    initial_prompt: 'Start the discussion',
    teaching_objectives: 'Encourage critical thinking',
    created_at: '2024-01-02T00:00:00Z',
    owner_id: null,
    is_global: true,
  },
];

/** Mock the auth endpoints used by the login flow. */
export async function mockAuthApi(page: Page): Promise<void> {
  await page.route('**/api/v1/auth/login', (route) =>
    route.fulfill({ json: mockLoginResponse }),
  );
  await page.route('**/api/v1/auth/session', (route) =>
    route.fulfill({ json: mockSessionResponse }),
  );
}

/** Mock the scenario list endpoint shown after login. */
export async function mockScenarioApi(page: Page): Promise<void> {
  await page.route('**/api/v1/scenario/get-all', (route) =>
    route.fulfill({ json: mockScenarios }),
  );
}

/** Log in through the UI with all backend calls mocked. */
export async function loginThroughUi(page: Page): Promise<void> {
  await mockAuthApi(page);
  await mockScenarioApi(page);
  await page.goto('/');
  await page.getByLabel('Email').fill('teacher@example.com');
  await page.getByLabel('Password').fill('password123');
  await page.getByRole('button', { name: 'Sign In' }).click();
}
