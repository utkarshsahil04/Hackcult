import { expect, test, type Page } from '@playwright/test'

async function openMonument(page: Page, slug: string) {
  await page.addInitScript(() => {
    sessionStorage.setItem('raahein-intro', '1')
    localStorage.setItem('raahein-language', 'en')
  })
  await page.route('**/api/stories/**', (route) => {
    const story_type = new URL(route.request().url()).searchParams.get('story_type') ?? 'visitor'
    return route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({ slug, language: 'en', story_type, body: `${story_type} story text for the test.`, audio_key: null, model_version: 'x', generated_at: 'x' }),
    })
  })
  await page.goto(`/monument/${slug}`)
}

test('story length tiers switch between visitor and scholar text', async ({ page }) => {
  await openMonument(page, 'taj-mahal')
  const story = page.getByRole('button', { name: 'Story', exact: true })
  await expect(story).toHaveAttribute('aria-pressed', 'true')
  await expect(page.getByText('visitor story text for the test.')).toBeVisible()
  await page.getByRole('button', { name: 'Scholar' }).click()
  await expect(page.getByRole('button', { name: 'Scholar' })).toHaveAttribute('aria-pressed', 'true')
  await expect(page.getByText('academic story text for the test.')).toBeVisible()
  await expect(page.getByTestId('facts')).toBeVisible()
})

test('share button shows only on verified monuments', async ({ page }) => {
  await openMonument(page, 'taj-mahal')
  await expect(page.getByRole('button', { name: 'Share' })).toBeVisible()
  await page.goto('/monument/india-gate')
  await expect(page.getByTestId('story-pending')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Share' })).toHaveCount(0)
})
