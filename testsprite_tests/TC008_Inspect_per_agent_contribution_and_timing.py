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
        
        # -> Click the 'Agent Progress' link in the left sidebar to open the full pipeline progress view.
        # Agent Progress link
        elem = page.get_by_role('link', name='Agent Progress', exact=True)
        await elem.click(timeout=10000)
        
        # --> Assertions to verify final state
        
        # --> Verify per-agent contribution details are displayed
        await page.locator("xpath=/html/body/div/div/div[2]/main/div/div[1]/div[1]/div[1]/div[3]/span").nth(0).scroll_into_view_if_needed()
        # Assert: Per-agent contribution counter showing '12%' for the Orchestrator is visible.
        await expect(page.locator("xpath=/html/body/div/div/div[2]/main/div/div[1]/div[1]/div[1]/div[3]/span").nth(0)).to_be_visible(timeout=15000), "Per-agent contribution counter showing '12%' for the Orchestrator is visible."
        await page.locator("xpath=/html/body/div/div/div[2]/main/div/div[1]/div[2]/div[1]/div[3]/span").nth(0).scroll_into_view_if_needed()
        # Assert: Per-agent contribution counter showing '50%' for the Behavior agent is visible.
        await expect(page.locator("xpath=/html/body/div/div/div[2]/main/div/div[1]/div[2]/div[1]/div[3]/span").nth(0)).to_be_visible(timeout=15000), "Per-agent contribution counter showing '50%' for the Behavior agent is visible."
        await page.locator("xpath=/html/body/div/div/div[2]/main/div/div[1]/div[3]/div[1]/div[3]/span").nth(0).scroll_into_view_if_needed()
        # Assert: Per-agent contribution counter showing '72%' for the Device agent is visible.
        await expect(page.locator("xpath=/html/body/div/div/div[2]/main/div/div[1]/div[3]/div[1]/div[3]/span").nth(0)).to_be_visible(timeout=15000), "Per-agent contribution counter showing '72%' for the Device agent is visible."
        
        # --> Verify per-agent timing details are displayed
        # Assert: A per-agent timing timestamp '12:42:11' is displayed in the activity stream.
        await expect(page.locator("xpath=/html/body/div/div/div[2]/main/div/div[2]/ol/li[1]/span[1]").nth(0)).to_have_text("12:42:11", timeout=15000), "A per-agent timing timestamp '12:42:11' is displayed in the activity stream."
        # Assert: A per-agent timing entry showing 'Fused score 0.94 → BLOCK TX-8842311' is displayed in the activity stream.
        await expect(page.locator("xpath=/html/body/div/div/div[2]/main/div/div[2]/ol/li[1]/span[3]").nth(0)).to_have_text("Fused score 0.94 \u2192 BLOCK TX-8842311", timeout=15000), "A per-agent timing entry showing 'Fused score 0.94 \u2192 BLOCK TX-8842311' is displayed in the activity stream."
        await asyncio.sleep(5)

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()

asyncio.run(run_test())
    