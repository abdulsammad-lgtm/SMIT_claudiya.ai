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
        
        # -> Click the 'Behavior' link in the left sidebar to open the Behavior agent detail page.
        # Behavior link
        elem = page.get_by_role('link', name='Behavior', exact=True)
        await elem.click(timeout=10000)
        
        # --> Assertions to verify final state
        
        # --> Verify session telemetry details are displayed
        # Assert: The live telemetry indicator is visible.
        await expect(page.locator("xpath=/html/body/div/div/div[2]/main/div/div[2]/div[1]/div[1]/span").nth(0)).to_have_text("live", timeout=15000), "The live telemetry indicator is visible."
        # Assert: The 'Dwell' biometric metric label is displayed.
        await expect(page.locator("xpath=/html/body/div/div/div[2]/main/div/div[2]/div[2]/div[3]/div[1]/div[1]/span[1]").nth(0)).to_have_text("Dwell", timeout=15000), "The 'Dwell' biometric metric label is displayed."
        # Assert: The Dwell biometric score '92' is shown.
        await expect(page.locator("xpath=/html/body/div/div/div[2]/main/div/div[2]/div[2]/div[3]/div[1]/div[1]/span[2]").nth(0)).to_have_text("92", timeout=15000), "The Dwell biometric score '92' is shown."
        
        # --> Verify behavior scoring metrics are displayed
        # Assert: Typing rhythm metric is visible as 72%.
        await expect(page.locator("xpath=/html/body/div/div/div[2]/main/div/div[2]/div[1]/div[4]/div[1]/div[1]/span[2]").nth(0)).to_have_text("72\n%", timeout=15000), "Typing rhythm metric is visible as 72%."
        # Assert: Dwell biometric score is visible as 92.
        await expect(page.locator("xpath=/html/body/div/div/div[2]/main/div/div[2]/div[2]/div[3]/div[1]/div[1]/span[2]").nth(0)).to_have_text("92", timeout=15000), "Dwell biometric score is visible as 92."
        # Assert: Flight biometric score is visible as 88.
        await expect(page.locator("xpath=/html/body/div/div/div[2]/main/div/div[2]/div[2]/div[3]/div[2]/div[1]/span[2]").nth(0)).to_have_text("88", timeout=15000), "Flight biometric score is visible as 88."
        await asyncio.sleep(5)

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()

asyncio.run(run_test())
    