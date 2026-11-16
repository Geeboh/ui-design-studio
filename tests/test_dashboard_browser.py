"""Real-browser regressions over synthetic, isolated runs.

Three lifecycle cases simulate persisted events. The history-navigation case uses
real browser Back and observes cache restoration or reload. These synthetic runs
do not establish application review evidence.
"""
from functools import partial
import base64
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import sys
import tempfile
import threading
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
        options = {"headless": True, "args": ["--no-sandbox"],
                   "ignore_default_args": ["--disable-back-forward-cache"]}
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

    def test_real_back_navigation_refreshes_runs_and_continues_polling(self):
        (self.repo / "away.html").write_text("<!doctype html><title>Away</title><h1>Away</h1>", encoding="utf-8")
        handler = partial(SimpleHTTPRequestHandler, directory=str(self.repo))
        with ThreadingHTTPServer(("127.0.0.1", 0), handler) as away:
            thread = threading.Thread(target=away.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
            thread.start()
            try:
                session = dashboard.DashboardSession(self.repo, host="127.0.0.1")
                self.addCleanup(session.close)
                session.start()
                page = self.page()
                page.add_init_script("""window.__historyProbe = {identity: crypto.randomUUID(), shows: []};
                    addEventListener("pageshow", event => __historyProbe.shows.push({
                        persisted: event.persisted, trusted: event.isTrusted
                    }));""")
                page.goto(session.info()["localUrl"])
                expect(page.locator("#connection-status")).to_have_text("Connected")
                original = page.evaluate("window.__historyProbe.identity")
                page.goto(f"http://localhost:{away.server_port}/away.html")
                expect(page.locator("h1")).to_have_text("Away")
                restored_run = self.new_run()
                page.go_back(wait_until="commit")
                expect(page.locator("#run-list")).to_contain_text(restored_run.name, timeout=8000)
                observed = page.evaluate("""original => ({
                    sameDocument: __historyProbe.identity === original,
                    ...__historyProbe.shows.at(-1),
                    reasons: performance.getEntriesByType("navigation")[0]
                        ?.notRestoredReasons?.reasons.map(entry => entry.reason) || []
                })""", original)
                self.assertTrue(observed["trusted"])
                self.assertEqual(observed["sameDocument"], observed["persisted"])
                later_run = self.new_run()
                expect(page.locator("#run-list")).to_contain_text(later_run.name, timeout=6000)
                expect(page.locator("#run-count")).to_have_text("2 recorded runs")
                expect(page.locator("#connection-status")).to_have_text("Connected")
                print(f"Real history navigation in Chromium {self.browser.version}: {observed}")
            finally:
                away.shutdown()
                thread.join()

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

    def test_guided_form_persists_exact_review_and_survives_reload(self):
        root = self.new_run()
        (root / "board.html").write_text("<!doctype html><title>Review board</title><h1>Review board</h1>", encoding="utf-8")
        self.backend.publish_artwork(self.engine, root, "board.html", "Synthetic form fixture.", title="Review board")
        request = self.backend.publish_request(
            self.engine, root, "form-review", "plan", "Review the board",
            "Synthetic approval fixture, not product acceptance.", ["board.html"],
        )["request"]
        server = self.backend.DesignServer(self.engine, root, interval=0.05)
        self.addCleanup(server.close)
        server.start()
        page = self.page()
        page.goto(server.url)
        expect(page.locator("#connection-status")).to_have_text("Connected")
        page.locator("#nav-approvals").click()
        card = page.locator('[data-approval-id="form-review"]')
        card.locator('input[name="optionId"][value="approve"]').check()
        card.locator('input[name="outcome"][value="approved"]').check()
        card.locator('textarea[name="rationale"]').fill("  The reviewed board preserves the required recovery state.  ")
        card.locator('input[name="reviewed"]').check()
        card.locator('button[type="submit"]').click()
        expect(card.locator(".approval-readonly")).to_contain_text("Recorded decision: approved.")
        decisions = self.engine.read_json(root / "decisions.json")["decisions"]
        self.assertEqual(len(decisions), 1)
        self.assertEqual(
            {key: decisions[0][key] for key in ("stage", "actor", "outcome", "rationale", "optionId", "requestId")},
            {"stage": "plan", "actor": "user", "outcome": "approved",
             "rationale": "The reviewed board preserves the required recovery state.",
             "optionId": "approve", "requestId": "form-review"},
        )
        self.assertEqual(decisions[0]["inputsDigest"], request["inputsDigest"])
        page.reload()
        expect(page.locator("#connection-status")).to_have_text("Connected")
        page.locator("#nav-approvals").click()
        expect(card.locator(".approval-readonly")).to_contain_text("Recorded decision: approved.")
        expect(card.locator(".approval-form")).to_be_hidden()

    def test_browser_submits_image_annotation_with_undo_redo(self):
        root = self.new_run()
        (root / "plan.html").write_text("<!doctype html><title>Review board</title><h1>Review board</h1>", encoding="utf-8")
        self.backend.publish_artwork(self.engine, root, "plan.html", "Synthetic form fixture.", title="Review board")
        request = self.backend.publish_request(
            self.engine, root, "annotated-browser-review", "plan", "Review the board",
            "Synthetic annotation fixture.", ["plan.html"],
        )["request"]
        server = self.backend.DesignServer(self.engine, root, interval=0.05)
        self.addCleanup(server.close)
        server.start()
        page = self.page()
        page.goto(server.url)
        expect(page.locator("#connection-status")).to_have_text("Connected")
        page.locator("#nav-approvals").click()
        card = page.locator('[data-approval-id="annotated-browser-review"]')
        card.locator('input[name="optionId"][value="approve"]').check()
        card.locator('input[name="outcome"][value="changes"]').check()
        card.locator('input[type="file"]').set_input_files({
            "name": "feedback.png",
            "mimeType": "image/png",
            "buffer": base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aT9sAAAAASUVORK5CYII="),
        })
        expect(card.locator(".annotation-stage")).to_be_visible()
        stage = card.locator(".annotation-stage")
        stage.scroll_into_view_if_needed()
        box = stage.bounding_box()
        self.assertIsNotNone(box)
        page.mouse.move(box["x"] + 20, box["y"] + 20)
        page.mouse.down()
        page.mouse.move(box["x"] + box["width"] - 20, box["y"] + box["height"] - 20)
        page.mouse.up()
        expect(card.get_by_role("button", name="Undo")).to_be_enabled()
        card.get_by_role("button", name="Undo").click()
        expect(card.get_by_role("button", name="Redo")).to_be_enabled()
        card.get_by_role("button", name="Redo").click()
        card.locator('textarea[name="rationale"]').fill("Move the focal point to the upper right.")
        card.locator('input[name="reviewed"]').check()
        page.screenshot(path="/tmp/ui-design-approval-annotations.png", full_page=True)
        card.locator('button[type="submit"]').click()
        expect(card.locator(".approval-readonly")).to_contain_text("Recorded decision: changes.")
        decision = self.engine.read_json(root / "decisions.json")["decisions"][-1]
        self.assertEqual(decision["attachments"][0]["name"], "feedback.png")
        self.assertEqual(decision["annotations"][0]["tool"], "arrow")

    def test_nested_configured_theme_approval_persists_through_browser_form(self):
        theme = self.repo / "branding/themes/fixture"
        theme.parent.mkdir(parents=True)
        (self.repo / "themes/fixture").rename(theme)
        self.engine.atomic_json(self.repo / "ui-design-studio.json",
                                {"paths": {"themes": "branding/themes", "runs": "work/docs/design/runs"}})
        root = self.new_run()
        server = self.backend.DesignServer(self.engine, root, interval=0.05, repo=self.repo)
        self.addCleanup(server.close)
        server.start()
        imported = "theme-artwork/fixture/preview.html"
        request = self.backend.publish_request(
            self.engine, root, "nested-form-review", "plan", "Review the configured theme",
            "Synthetic nested-root browser fixture.", [imported], repo=self.repo,
        )["request"]
        page = self.page()
        page.goto(server.url)
        expect(page.locator("#connection-status")).to_have_text("Connected")
        page.locator("#nav-approvals").click()
        card = page.locator('[data-approval-id="nested-form-review"]')
        expect(card.locator(".approval-inputs")).to_contain_text(imported)
        card.locator('input[name="optionId"][value="approve"]').check()
        card.locator('input[name="outcome"][value="approved"]').check()
        card.locator('textarea[name="rationale"]').fill("The configured theme matches the reviewed artifact.")
        card.locator('input[name="reviewed"]').check()
        card.locator('button[type="submit"]').click()
        expect(card.locator(".approval-readonly")).to_contain_text("Recorded decision: approved.")
        page.reload()
        expect(page.locator("#connection-status")).to_have_text("Connected")
        page.locator("#nav-approvals").click()
        expect(card.locator(".approval-form")).to_be_hidden()
        decisions = self.engine.read_json(root / "decisions.json")["decisions"]
        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0]["inputsDigest"], request["inputsDigest"])
        self.assertIn(imported, decisions[0]["inputs"])
        self.assertEqual(decisions[0]["actor"], "user")
        sources = self.engine.read_json(root / ".design-theme-sources.json")
        self.assertEqual(sources["projectRoot"], str(self.repo))
        self.assertEqual(sources["themePath"], "branding/themes/fixture")
    def test_svg_artwork_renders_and_newest_approval_is_first(self):
        root = self.new_run()
        (root / "plan.html").write_text("<!doctype html><title>Review board</title><h1>Review board</h1>", encoding="utf-8")
        (root / "diagram.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><rect width="10" height="10"/></svg>',
            encoding="utf-8",
        )
        artwork = self.backend.publish_artwork(self.engine, root, "diagram.svg", "Synthetic SVG preview.")["artwork"]
        self.backend.publish_request(
            self.engine, root, "z-review", "plan", "Newer review",
            "Synthetic approval fixture.", ["plan.html"],
        )
        server = self.backend.DesignServer(self.engine, root, interval=0.05)
        self.addCleanup(server.close)
        server.start()
        page = self.page()
        page.goto(server.url)
        expect(page.locator("#connection-status")).to_have_text("Connected")
        page.locator("#nav-progress").click()
        expect(page.locator("#phase-list")).to_contain_text("Build / Produce")
        page.screenshot(path="/tmp/ui-design-progress.png", full_page=True)
        page.locator("#nav-library").click()
        expect(page.locator("#library-versions")).to_have_value("latest")
        page.screenshot(path="/tmp/ui-design-library.png", full_page=True)
        page.locator("#nav-approvals").click()
        page.screenshot(path="/tmp/ui-design-approvals.png", full_page=True)
        expect(page.locator(".approval-card").nth(0)).to_have_attribute("data-approval-id", "z-review")
        self.backend.publish_request(
            self.engine, root, "a-review", "plan", "Older review",
            "Synthetic approval fixture.", ["plan.html"],
        )
        expect(page.locator(".approval-card").nth(0)).to_have_attribute("data-approval-id", "a-review")
        page.locator("#nav-feed").click()
        card = page.locator('[data-artwork-id="' + artwork["id"] + '"]')
        card.scroll_into_view_if_needed()
        card.locator(".artwork-open").click()
        image = page.locator("#viewer-content img")
        expect(image).to_be_visible()
        self.assertGreater(image.evaluate("(node) => node.naturalWidth"), 0)

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
        expect(page.locator("#artwork-dialog")).to_be_hidden()
        replacement = card.locator('.approval-readonly-options button[data-artwork-id]')
        page.locator("#completed-approvals > summary").click()
        expect(replacement).to_be_visible()
        expect(replacement).to_be_enabled()
        self.assertTrue(replacement.is_visible())


if __name__ == "__main__":
    unittest.main()
