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
        engine_name = os.environ.get("UI_DESIGN_TEST_ENGINE", "chromium").lower()
        if engine_name not in {"chromium", "firefox", "webkit"}:
            raise unittest.SkipTest(f"Unsupported browser engine: {engine_name}")
        options = {"headless": True, "ignore_default_args": ["--disable-back-forward-cache"]}
        if engine_name != "webkit":
            options["args"] = ["--no-sandbox"]
        executable = os.environ.get("UI_DESIGN_TEST_BROWSER")
        if executable:
            options["executable_path"] = executable
        cls.browser_engine = engine_name
        cls.browser = getattr(cls.playwright, engine_name).launch(**options)
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
                print(f"Real history navigation in {self.browser_engine} {self.browser.version}: {observed}")
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

    def test_unsubmitted_approval_draft_survives_reload(self):
        root = self.new_run()
        (root / "draft.html").write_text("<!doctype html><title>Draft board</title><h1>Draft board</h1>", encoding="utf-8")
        self.backend.publish_artwork(self.engine, root, "draft.html", "Synthetic draft fixture.", title="Draft board")
        self.backend.publish_request(self.engine, root, "draft-review", "plan", "Review the draft", "Synthetic draft fixture.", ["draft.html"])
        server = self.backend.DesignServer(self.engine, root, interval=0.05)
        self.addCleanup(server.close)
        server.start()
        page = self.page()
        page.goto(server.url)
        expect(page.locator("#connection-status")).to_have_text("Connected")
        page.locator("#nav-approvals").click()
        card = page.locator('[data-approval-id="draft-review"]')
        card.locator('input[name="optionId"][value="approve"]').check()
        card.locator('input[name="outcome"][value="approved"]').check()
        card.locator('textarea[name="rationale"]').fill("Keep the approved spacing and continue the review.")
        page.reload()
        expect(page.locator("#connection-status")).to_have_text("Connected")
        page.locator("#nav-approvals").click()
        expect(card.locator('textarea[name="rationale"]')).to_have_value("Keep the approved spacing and continue the review.")
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
        coordinate_fields = card.locator(".annotation-coordinates input")
        for field, value in zip([coordinate_fields.nth(index) for index in range(4)], ("0.1", "0.2", "0.8", "0.9")):
            field.fill(value)
        card.get_by_role("button", name="Add from coordinates").click()
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
        self.assertEqual(decision["annotations"][0]["points"], [[0.1, 0.2], [0.8, 0.9]])

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
        self.backend.publish_artwork(self.engine, root, "diagram.svg", "Synthetic SVG baseline.", title="Diagram baseline")
        (root / "diagram.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><rect width="5" height="10"/></svg>',
            encoding="utf-8",
        )
        artwork = self.backend.publish_artwork(self.engine, root, "diagram.svg", "Synthetic SVG preview.", title="Diagram current")["artwork"]
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
        expect(page.locator("#artwork-dialog")).to_be_visible(timeout=8000)
        image = page.locator("#viewer-content img")
        expect(image).to_be_visible(timeout=15000)
        compare = page.locator("#viewer-compare")
        expect(compare).to_be_visible()
        compare.click()
        expect(page.locator(".viewer-comparison-item")).to_have_count(2)
        expect(page.locator(".viewer-comparison-label").nth(0)).to_contain_text("Previous")
        expect(page.locator(".viewer-comparison-label").nth(1)).to_contain_text("Current")
        compare.click()
        expect(page.locator("#viewer-content img")).to_be_visible()
        self.assertGreater(image.evaluate("(node) => node.naturalWidth"), 0)

    def test_usage_panel_shows_recorded_tokens_and_cost(self):
        root = self.new_run()
        self.backend.record_usage(self.engine, root, {
            "usageId": "browser-usage", "idempotencyKey": "browser-attempt", "sessionId": "browser-session",
            "providerObserved": "fixture-provider", "modelObserved": "fixture-model", "agentId": "director",
            "executionStatus": "completed", "tokens": {"input": 100, "output": 25, "cacheRead": 40, "cacheWrite": 5},
            "cost": {"actual": {"status": "observed", "amountMinor": 123, "currencyCode": "USD", "currencyExponent": 2, "source": "fixture", "observedAt": self.backend.timestamp()}},
        })
        server = self.backend.DesignServer(self.engine, root, interval=0.05)
        self.addCleanup(server.close)
        server.start()
        page = self.page()
        page.goto(server.url)
        expect(page.locator("#connection-status")).to_have_text("Connected")
        page.locator("#nav-usage").click()
        expect(page.locator("#usage-heading")).to_be_visible()
        expect(page.locator("#usage-requests")).to_have_text("1")
        expect(page.locator("#usage-input")).to_have_text("100")
        expect(page.locator("#usage-output")).to_have_text("25")
        expect(page.locator("#usage-actual-cost")).to_contain_text("USD 1.23")
        expect(page.locator("#usage-export-json")).to_be_visible()
        page.locator('[data-usage-range="7d"]').click()
        expect(page.locator("#usage-status")).to_have_text("Recorded")

    def test_usage_navigation_and_range_controls_work_by_keyboard(self):
        root = self.new_run()
        server = self.backend.DesignServer(self.engine, root, interval=0.05)
        self.addCleanup(server.close)
        server.start()
        page = self.page()
        page.goto(server.url)
        expect(page.locator("#connection-status")).to_have_text("Connected")
        page.locator("#nav-usage").focus()
        page.locator("#nav-usage").press("Enter")
        expect(page.locator("#usage-heading")).to_be_visible()
        page.locator('[data-usage-range="7d"]').focus()
        page.locator('[data-usage-range="7d"]').press("Enter")
        expect(page.locator('[data-usage-range="7d"]')).to_have_attribute("aria-pressed", "true")
    def test_narrow_reflow_reduced_motion_and_text_contrast(self):
        root = self.new_run()
        server = self.backend.DesignServer(self.engine, root, interval=0.05)
        self.addCleanup(server.close)
        server.start()
        page = self.page()
        page.set_viewport_size({"width": 320, "height": 800})
        page.emulate_media(reduced_motion="reduce")
        page.goto(server.url)
        expect(page.locator("#connection-status")).to_have_text("Connected")
        self.assertTrue(page.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches"))
        self.assertTrue(page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"))
        transition = page.locator("#refresh-snapshot").evaluate("(node) => getComputedStyle(node).transitionDuration")
        self.assertIn(transition, {"0s", "0ms"})
        contrast = page.evaluate("""() => {
            const style = getComputedStyle(document.documentElement);
            const parse = value => value.match(/[0-9a-f]{2}/gi).map(part => parseInt(part, 16) / 255);
            const [r1, g1, b1] = parse(style.getPropertyValue('--text'));
            const [r2, g2, b2] = parse(style.getPropertyValue('--canvas'));
            const lum = (r, g, b) => [r, g, b].map(value => value <= 0.03928 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4).reduce((sum, value, index) => sum + value * [0.2126, 0.7152, 0.0722][index], 0);
            const light = Math.max(lum(r1, g1, b1), lum(r2, g2, b2));
            const dark = Math.min(lum(r1, g1, b1), lum(r2, g2, b2));
            return (light + 0.05) / (dark + 0.05);
        }""")
        self.assertGreaterEqual(contrast, 4.5)
        if self.browser_engine == "chromium":
            cdp = page.context.new_cdp_session(page)
            cdp.send("Emulation.setPageScaleFactor", {"pageScaleFactor": 2})
            self.assertEqual(page.evaluate("visualViewport.scale"), 2)
            cdp.send("Emulation.setPageScaleFactor", {"pageScaleFactor": 4})
            self.assertEqual(page.evaluate("visualViewport.scale"), 4)
            cdp.send("Emulation.setPageScaleFactor", {"pageScaleFactor": 1})
        page.locator("#nav-usage").focus()
        target = page.locator("#nav-usage").bounding_box()
        self.assertGreaterEqual(target["width"], 40)
        self.assertGreaterEqual(target["height"], 40)


    def test_cancel_and_reconcile_render_unknown_remote_outcome(self):
        root = self.new_run()
        server = self.backend.DesignServer(self.engine, root, interval=0.05)
        self.addCleanup(server.close)
        server.start()
        page = self.page()
        page.goto(server.url)
        expect(page.locator("#connection-status")).to_have_text("Connected")
        expect(page.locator("#cancel-run")).to_be_enabled()
        page.locator("#cancel-run").click()
        expect(page.locator("#run-status")).to_have_text("cancelled")
        expect(page.locator("#run-detail")).to_contain_text("remote outcome unknown")
        expect(page.locator("#reconcile-run")).to_be_visible()
        page.locator("#reconcile-run").click()
        expect(page.locator("#run-status")).to_have_text("reconciling")
        expect(page.locator("#run-detail")).to_contain_text("cancellation reconciling")

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
