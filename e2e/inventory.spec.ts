import { test, expect } from '@playwright/test';

test.use({
    browserName: 'firefox',
});

test('has title', async ({ page }) => {
  await page.goto('http://localhost:8081/');
  // Make sure we have the right title
  await expect(page).toHaveTitle(/PySheets/);
});

test('has new button', async ({ page }) => {
  await page.goto('http://localhost:8081/');
  // Find the new button and make sure it exists
  await expect(page.locator('.new-button')).toHaveText('New Sheet');
});

test('create new sheet', async ({ page }) => {
  await page.goto('http://localhost:8081/');
  // Click the new button and create a new sheet
  await page.locator('.new-button').click();
  // Make sure we have the right title
  await expect(page).toHaveTitle(/Untitled Sheet/);
  // Change the title by editing it
  await page.locator('#title').fill('New Sheet');
  await page.locator('#main').focus();
  // Make sure we have the right title
  await expect(page).toHaveTitle(/New Sheet/);
});
