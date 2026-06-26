import asyncio
import re
from playwright import async_api
from playwright.async_api import expect

async def run_test():
    pw = None
    browser = None
    context = None

    try:
        # Start a Playwright session in asynchronous mode
        pw = await async_api.async_playwright().start()

        # Launch a Chromium browser in headless mode with custom arguments
        browser = await pw.chromium.launch(
            headless=True,
            args=[
                "--window-size=1280,720",
                "--disable-dev-shm-usage",
                "--ipc=host",
                "--single-process"
            ],
        )

        # Create a new browser context (like an incognito window)
        context = await browser.new_context()
        # Wider default timeout to match the agent's DOM-stability budget;
        # auto-waiting Playwright APIs (expect, locator.wait_for) inherit this.
        context.set_default_timeout(15000)

        # Open a new page in the browser context
        page = await context.new_page()

        # Interact with the page elements to simulate user flow
        # -> navigate
        await page.goto("http://127.0.0.1:3001/")
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass
        
        # -> Scroll down to reveal the 'Risk surface · last 24h' KPI card and the 'Live threat feed' transactions so their content is visible in the viewport for visual verification.
        await page.mouse.wheel(0, 300)
        
        # --> Assertions to verify final state
        
        # --> Verify live KPI metrics are displayed
        # Assert: The Americas KPI label is visible.
        await expect(page.locator("xpath=/html/body/div/div/div[2]/main/section[1]/div[3]/div[2]/div[1]/div[1]/span[1]").nth(0)).to_have_text("Americas", timeout=15000), "The Americas KPI label is visible."
        # Assert: The EMEA KPI label is visible.
        await expect(page.locator("xpath=/html/body/div/div/div[2]/main/section[1]/div[3]/div[2]/div[2]/div[1]/span[1]").nth(0)).to_have_text("EMEA", timeout=15000), "The EMEA KPI label is visible."
        # Assert: The APAC KPI label is visible.
        await expect(page.locator("xpath=/html/body/div/div/div[2]/main/section[1]/div[3]/div[2]/div[3]/div[1]/span[1]").nth(0)).to_have_text("APAC", timeout=15000), "The APAC KPI label is visible."
        # Assert: The LATAM KPI label is visible.
        await expect(page.locator("xpath=/html/body/div/div/div[2]/main/section[1]/div[3]/div[2]/div[4]/div[1]/span[1]").nth(0)).to_have_text("LATAM", timeout=15000), "The LATAM KPI label is visible."
        
        # --> Verify the transaction activity list is displayed
        await page.locator("xpath=/html/body/div/div/div[2]/main/section[3]/div[2]/ul/li[1]/div[1]").nth(0).scroll_into_view_if_needed()
        # Assert: The first transaction in the Live threat feed is visible.
        await expect(page.locator("xpath=/html/body/div/div/div[2]/main/section[3]/div[2]/ul/li[1]/div[1]").nth(0)).to_be_visible(timeout=15000), "The first transaction in the Live threat feed is visible."
        await page.locator("xpath=/html/body/div/div/div[2]/main/section[3]/div[2]/ul/li[2]/div[1]").nth(0).scroll_into_view_if_needed()
        # Assert: A second transaction entry in the Live threat feed is visible.
        await expect(page.locator("xpath=/html/body/div/div/div[2]/main/section[3]/div[2]/ul/li[2]/div[1]").nth(0)).to_be_visible(timeout=15000), "A second transaction entry in the Live threat feed is visible."
        await page.locator("xpath=/html/body/div/div/div[2]/main/section[3]/div[2]/ul/li[3]/div[1]").nth(0).scroll_into_view_if_needed()
        # Assert: A third transaction entry in the Live threat feed is visible.
        await expect(page.locator("xpath=/html/body/div/div/div[2]/main/section[3]/div[2]/ul/li[3]/div[1]").nth(0)).to_be_visible(timeout=15000), "A third transaction entry in the Live threat feed is visible."
        await page.locator("xpath=/html/body/div/div/div[2]/main/section[3]/div[2]/ul/li[4]/div[1]").nth(0).scroll_into_view_if_needed()
        # Assert: A fourth transaction entry in the Live threat feed is visible.
        await expect(page.locator("xpath=/html/body/div/div/div[2]/main/section[3]/div[2]/ul/li[4]/div[1]").nth(0)).to_be_visible(timeout=15000), "A fourth transaction entry in the Live threat feed is visible."
        await asyncio.sleep(5)

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()

asyncio.run(run_test())
    