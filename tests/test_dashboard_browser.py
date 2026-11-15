"""Real-browser regressions over synthetic, isolated runs.

Persisted lifecycle events are simulated. These tests do not verify native BFCache
or establish application review evidence.
"""
import os
from pathlib import Path
import sys
import tempfile
import unittest

try:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, expect, sync_playwright
except ImportError:
    sync_playwright = None

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ui_design_studio import dashboard
from ui_design_studio.runtime import backend, studio
from test_studio import fixture_theme


@unittest.skipIf(sync_playwright is None, "Playwright is not installed")
class DashboardBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.addClassCleanup(cls.playwright.stop)
        options = {"headless": True, "args": ["--no-sandbox"]}
        executable = os.environ.get("UI_DESIGN_TEST_BROWSER")
        if executable:
            options["executable_path"] = executable
        cls.browser = cls.playwright.chromium.launch(**options)
        cls.addClassCleanup(cls.browser.close)

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name).resolve()
        fixture_theme(self.repo)
        self.engine = studio()
        self.backend = backend()

    def page(self):
        page = self.browser.new_page()
        self.addCleanup(page.close)
        page.set_default_timeout(8000)
        return page

    def new_run(self):
        return Path(self.engine.init_run(self.repo, theme_id="fixture")["run"])

    def landing(self):
        session = dashboard.DashboardSession(self.repo, host="127.0.0.1")
        self.addCleanup(session.close)
        session.start()
        page = self.page()
        page.goto(session.info()["localUrl"])
        expect(page.locator("#connection-status")).to_have_text("Connected")
        expect(page.locator("#refresh-session")).to_be_enabled()
        return session, page

    def test_landing_resumes_polling_after_simulated_persisted_restore(self):
        session, page = self.landing()
        expect(page.locator("#run-count")).to_have_text("0 recorded runs")
        page.evaluate('() => window.dispatchEvent(new PageTransitionEvent("pagehide", {persisted: true}))')
        restored_run = self.new_run()
        page.evaluate('() => window.dispatchEvent(new PageTransitionEvent("pageshow", {persisted: true}))')
        expect(page.locator("#run-list")).to_contain_text(restored_run.name, timeout=6000)
        expect(page.locator("#connection-status")).to_have_text("Connected")
        later_run = self.new_run()
        expect(page.locator("#run-list")).to_contain_text(later_run.name, timeout=6000)
        expect(page.locator("#run-count")).to_have_text("2 recorded runs")

    def test_landing_cancels_hidden_poll_before_simulated_restore(self):
        session, page = self.landing()
        with session._lock:
            with page.expect_request("**/api/session"):
                page.locator("#refresh-session").click()
            expect(page.locator("#refresh-session")).to_be_disabled()
            page.evaluate('() => window.dispatchEvent(new PageTransitionEvent("pagehide", {persisted: true}))')
        with self.assertRaises(PlaywrightTimeoutError):
            with page.expect_request("**/api/session", timeout=2500):
                pass
        expect(page.locator("#connection-status")).to_have_text("Connected")
        restored_run = self.new_run()
        page.evaluate('() => window.dispatchEvent(new PageTransitionEvent("pageshow", {persisted: true}))')
        expect(page.locator("#run-list")).to_contain_text(restored_run.name, timeout=6000)
        expect(page.locator("#refresh-session")).to_be_enabled()

    def test_landing_restarts_in_flight_poll_after_simulated_persisted_restore(self):
        session, page = self.landing()
        restored_run = self.new_run()
        with session._lock:
            with page.expect_request("**/api/session"):
                page.locator("#refresh-session").click()
            expect(page.locator("#refresh-session")).to_be_disabled()
            with page.expect_request("**/api/session"):
                page.evaluate('''() => {
                    window.dispatchEvent(new PageTransitionEvent("pagehide", {persisted: true}));
                    window.dispatchEvent(new PageTransitionEvent("pageshow", {persisted: true}));
                    window.dispatchEvent(new PageTransitionEvent("pageshow", {persisted: true}));
                }''')
        expect(page.locator("#run-list")).to_contain_text(restored_run.name, timeout=6000)
        expect(page.locator("#connection-status")).to_have_text("Connected")
        expect(page.locator("#refresh-session")).to_be_enabled()
        later_run = self.new_run()
        expect(page.locator("#run-list")).to_contain_text(later_run.name, timeout=6000)

    def test_artwork_close_focus_survives_concurrent_approval(self):
        root = self.new_run()
        (root / "a.html").write_text("<!doctype html><title>Focus board</title><h1>Synthetic focus board</h1>", encoding="utf-8")
        self.backend.publish_artwork(self.engine, root, "a.html", "Synthetic focus regression artwork.", title="Focus board")
        request = self.backend.publish_request(
            self.engine, root, "focus-review", "plan", "Review the focus board",
            "Synthetic approval fixture, not an application review.", ["a.html"],
        )["request"]
        server = self.backend.DesignServer(self.engine, root, interval=0.05)
        self.addCleanup(server.close)
        server.start()
        page = self.page()
        page.goto(server.url)
        expect(page.locator("#connection-status")).to_have_text("Connected")
        page.locator("#nav-approvals").click()
        card = page.locator('[data-approval-id="focus-review"]')
        original = card.locator('.approval-form button[data-artwork-id]')
        original.click()
        expect(page.locator("#artwork-dialog")).to_be_visible()
        page.locator("#viewer-close").click()
        expect(original).to_be_focused()
        original.click()
        expect(page.locator("#artwork-dialog")).to_be_visible()
        self.backend.approve(self.engine, root, {
            "id": request["id"], "inputsDigest": request["inputsDigest"],
            "optionId": "approve", "outcome": "approved",
            "rationale": "Synthetic concurrent review of the exact fixture inputs.",
        })
        expect(card.locator(".approval-form")).to_have_attribute("hidden", "", timeout=8000)
        expect(card.locator(".approval-readonly")).to_contain_text("Recorded decision: approved.")
        page.locator("#viewer-close").click()
        replacement = card.locator('.approval-readonly-options button[data-artwork-id]')
        expect(page.locator("#artwork-dialog")).to_be_hidden()
        expect(replacement).to_be_visible()
        expect(replacement).to_be_enabled()
        expect(replacement).to_be_focused()


if __name__ == "__main__":
    unittest.main()
