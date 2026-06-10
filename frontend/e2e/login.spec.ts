import { test, expect } from '@playwright/test';
import { loginThroughUi, mockAuthApi } from './fixtures';

test.describe('Login page', () => {
  test('renders the login form', async ({ page }) => {
    await page.goto('/');

    await expect(page.locator('img.brand-logo')).toBeVisible();
    await expect(page.getByLabel('Email')).toBeVisible();
    await expect(page.getByLabel('Password')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Sign In' })).toBeDisabled();
  });

  test('keeps submit disabled until the form is valid', async ({ page }) => {
    await page.goto('/');

    const submit = page.getByRole('button', { name: 'Sign In' });
    await page.getByLabel('Email').fill('teacher@example.com');
    await expect(submit).toBeDisabled();

    await page.getByLabel('Password').fill('short');
    await expect(submit).toBeDisabled();

    await page.getByLabel('Password').fill('password123');
    await expect(submit).toBeEnabled();
  });

  test('shows an error when credentials are rejected', async ({ page }) => {
    await page.route('**/api/v1/auth/login', (route) =>
      route.fulfill({ status: 401, json: { detail: 'Incorrect email or password' } }),
    );
    await page.goto('/');

    await page.getByLabel('Email').fill('teacher@example.com');
    await page.getByLabel('Password').fill('wrongpassword');
    await page.getByRole('button', { name: 'Sign In' }).click();

    await expect(page.locator('.error-message')).toBeVisible();
    await expect(page).toHaveURL('/');
  });

  test('logs in and redirects to scenario selection', async ({ page }) => {
    await loginThroughUi(page);

    await expect(page).toHaveURL(/\/app\/scenario-selection/);
    await expect(page.getByRole('heading', { name: 'Welcome Back, Teacher!' })).toBeVisible();
  });

  test('navigates to the registration page', async ({ page }) => {
    await page.goto('/');

    await page.getByRole('link', { name: 'Create one' }).click();
    await expect(page).toHaveURL(/\/register/);
  });

  test('sends login credentials as form data', async ({ page }) => {
    await mockAuthApi(page);
    await page.goto('/');

    const loginRequest = page.waitForRequest('**/api/v1/auth/login');
    await page.getByLabel('Email').fill('teacher@example.com');
    await page.getByLabel('Password').fill('password123');
    await page.getByRole('button', { name: 'Sign In' }).click();

    const request = await loginRequest;
    expect(request.method()).toBe('POST');
    expect(request.postData()).toContain('username=teacher%40example.com');
    expect(request.postData()).toContain('grant_type=password');
  });
});

test.describe('Route guarding', () => {
  test('redirects unauthenticated users back to login', async ({ page }) => {
    await page.goto('/app/scenario-selection');

    await expect(page).toHaveURL('/');
    await expect(page.getByRole('button', { name: 'Sign In' })).toBeVisible();
  });
});
