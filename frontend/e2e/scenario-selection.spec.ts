import { test, expect } from '@playwright/test';
import { loginThroughUi, mockScenarios } from './fixtures';

test.describe('Scenario selection', () => {
  test.beforeEach(async ({ page }) => {
    await loginThroughUi(page);
    await expect(page).toHaveURL(/\/app\/scenario-selection/);
  });

  test('lists scenarios returned by the API', async ({ page }) => {
    for (const scenario of mockScenarios) {
      await expect(page.getByRole('heading', { name: scenario.name })).toBeVisible();
    }
    await expect(page.locator('.scenario-card')).toHaveCount(mockScenarios.length);
  });

  test('marks global scenarios with a badge', async ({ page }) => {
    const firstCard = page.locator('.scenario-card').first();
    await expect(firstCard.locator('.scenario-type-badge')).toContainText('Global');
  });

  test('selecting a scenario navigates to the overview', async ({ page }) => {
    await page.route('**/api/v1/scenario/set-current-by-id', (route) =>
      route.fulfill({ json: mockScenarios[0] }),
    );

    const firstCard = page.locator('.scenario-card').first();
    await firstCard.getByRole('button').click();

    await expect(page).toHaveURL(/\/app\/scenario-overview/);
  });
});
