"""Optional Selenium/Firefox checks; the website itself has no dependencies."""

import argparse
import json
import shutil
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait


ROOT = Path(__file__).resolve().parents[1]


class FixtureHandler(SimpleHTTPRequestHandler):
    """Mount the site under a project prefix, optionally substituting release info."""

    configured = False
    failures = []

    def do_GET(self):
        self.path = self.path.removeprefix("/eva-preview") or "/"
        if self.path == "/site.config.js" and self.configured:
            body = "window.EVA_CONFIG = " + json.dumps({
                "authors": [
                    {"name": "Alice Example", "url": "https://example.org/alice", "affiliation": "Example Lab"},
                    {"name": "Bob Example", "url": "javascript:alert(1)"},
                ],
                "affiliations": ["Example Lab"],
                "paperUrl": "assets/eva.pdf",
                "codeUrl": "https://github.com/example/eva",
                "year": "2027",
                "canonicalUrl": "https://example.github.io/eva/",
            }) + ";"
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript")
            self.end_headers()
            self.wfile.write(body.encode())
            return
        super().do_GET()

    def log_message(self, *_):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def send_error(self, code, message=None, explain=None):
        self.failures.append((code, self.path))
        super().send_error(code, message, explain)


def check(url):
    output = ROOT / "test-results"
    output.mkdir(exist_ok=True)
    options = Options()
    options.add_argument("-headless")
    options.enable_bidi = True
    options.set_preference("ui.prefersReducedMotion", 1)
    options.set_preference("media.autoplay.default", 0)
    snap_binary = Path("/snap/firefox/current/usr/lib/firefox/firefox")
    if snap_binary.exists():
        options.binary_location = str(snap_binary)
    elif shutil.which("firefox"):
        options.binary_location = shutil.which("firefox")
    driver = webdriver.Firefox(options=options, service=Service(service_args=["--allow-system-access"]))
    # Firefox's desktop browser chrome otherwise enforces a 500px minimum.
    try:
        driver.set_context("chrome")
        driver.execute_script("document.documentElement.style.minWidth='0px'; document.documentElement.style.minHeight='0px';")
        driver.set_context("content")
    except Exception:
        driver.quit()
        raise
    wait = WebDriverWait(driver, 20)
    errors = []
    driver.script.add_javascript_error_handler(lambda error: errors.append(str(error)))
    fixture = ThreadingHTTPServer(("127.0.0.1", 0), partial(FixtureHandler, directory=str(ROOT)))
    threading.Thread(target=fixture.serve_forever, daemon=True).start()
    fixture_url = f"http://127.0.0.1:{fixture.server_port}/eva-preview/"

    def js(script, *args):
        return driver.execute_script(script, *args)

    def find(selector):
        return driver.find_element(By.CSS_SELECTOR, selector)

    def click(selector):
        element = find(selector)
        js("arguments[0].scrollIntoView({block:'center',behavior:'instant'})", element)
        element.click()

    def ready():
        wait.until(lambda _: js("return document.querySelectorAll('.site-header svg').length > 0"))

    try:
        driver.get(url)
        ready()
        assert driver.title == "EVA | Video Demos"
        assert not driver.find_elements(By.CSS_SELECTOR, '.hero, .paper-section, #authors, #resources, [data-lightbox]')
        assert len(driver.find_elements(By.CSS_SELECTOR, 'video')) == 4
        assert len(driver.find_elements(By.CSS_SELECTOR, '[data-demo]')) == 4
        assert js("return document.querySelector('.demo-section').id") == "simulation-demos"
        assert not driver.find_elements(By.ID, 'demo-speed')
        assert not driver.find_elements(By.CSS_SELECTOR, '.intro-summary, .intro-actions, .review-note, #demo-description, .section-summary')
        assert js("return [...document.querySelectorAll('a[href^=\"#\"]')].every(a => document.querySelector(a.getAttribute('href')))")
        # Load the small thumbnails before capturing full-page screenshots;
        # otherwise off-screen lazy images can appear blank in the capture.
        js("document.querySelectorAll('img[loading]').forEach(img => img.loading = 'eager')")
        wait.until(lambda _: js("return [...document.images].every(img => img.complete && img.naturalWidth > 0)"))
        for width, height in [(1440, 1000), (1920, 1080), (800, 1000), (390, 844), (320, 740)]:
            driver.set_window_size(width, height)
            js("window.scrollTo({top:0,behavior:'instant'})")
            assert js("return document.documentElement.scrollWidth <= innerWidth"), width
            driver.get_full_page_screenshot_as_file(str(output / f"page-{width}.png"))
            print(f"PASS: {width}px viewport, no horizontal overflow")

        for width in [1440, 390, 320]:
            driver.set_window_size(width, 1000)
            for key, expected_width, expected_height in [("baseline", 1280, 830), ("monitor", 1280, 844), ("recovery", 1280, 824)]:
                selector = f"#sim-{key}-video"
                video = find(selector)
                js("arguments[0].scrollIntoView({block:'center',behavior:'instant'})", video)
                assert js("return document.documentElement.scrollWidth <= innerWidth")
                js("arguments[0].muted=true; arguments[0].play()", video)
                wait.until(lambda _, video=video: js("return arguments[0].currentTime > .1", video))
                state = js("return {width:arguments[0].videoWidth,height:arguments[0].videoHeight,error:arguments[0].error?.message}", video)
                assert state == {"width": expected_width, "height": expected_height, "error": None}, state
                js("arguments[0].pause()", video)
                driver.save_screenshot(str(output / f"sim-{key}-{width}.png"))
        driver.set_window_size(320, 740)
        print("PASS: all three simulation videos decode at native aspect ratios on desktop and mobile")

        click(".menu-toggle")
        assert find("#mobile-nav").is_displayed()
        click('#mobile-nav a[href="#simulation-demos"]')
        assert not find("#mobile-nav").is_displayed()
        click(".menu-toggle")
        find(".menu-toggle").send_keys(Keys.ESCAPE)
        assert not find("#mobile-nav").is_displayed()
        print("PASS: mobile navigation")

        for key in ["box", "chair", "memory", "bottles"]:
            click(f'[data-demo="{key}"]')
            assert find(f'[data-demo="{key}"]').get_attribute('aria-pressed') == 'true'
            assert len(driver.find_elements(By.CSS_SELECTOR, '.demo-choice[aria-pressed="true"]')) == 1
            js("const v=document.getElementById('demo-video'); v.muted=true; v.play().catch(e=>window.videoError=e.message)")
            wait.until(lambda _: js("return document.getElementById('demo-video').currentTime > .1"))
            state = js("const v=document.getElementById('demo-video'); return {width:v.videoWidth,height:v.videoHeight,error:v.error?.message}")
            assert state["width"] > 0 and state["height"] > 0 and not state["error"], state
            js("document.getElementById('demo-video').pause()")
        print("PASS: all four real-world videos decode and play")
        driver.set_window_size(1440, 1000)
        js("document.getElementById('real-world').scrollIntoView({behavior:'instant'})")
        driver.save_screenshot(str(output / "demos-desktop.png"))

        # Validate every public asset URL, including lazily loaded media.
        paths = js("return [...document.querySelectorAll('img[src],script[src],link[href],video[poster],source[src]')].flatMap(e => [e.src,e.poster,e.href]).filter(Boolean)")
        for path in set(paths):
            if urlsplit(path).netloc != urlsplit(url).netloc:
                continue
            with urlopen(Request(path, method="HEAD")) as response:
                assert response.status == 200, path

        driver.get(fixture_url)
        ready()
        assert "/eva-preview/" in find("#demo-video source").get_attribute("src")
        click('[data-demo="box"]')
        assert "/eva-preview/assets/videos/box.mp4" in find("#demo-video source").get_attribute("src")
        for key in ["baseline", "monitor", "recovery"]:
            assert f"/eva-preview/assets/videos/sim-{key}.mp4" in find(f"#sim-{key}-video source").get_attribute("src")
        FixtureHandler.configured = True
        driver.get(fixture_url)
        ready()
        assert find('meta[property="og:image"]').get_attribute("content") == "https://example.github.io/eva/assets/images/bottles.jpg"
        assert not FixtureHandler.failures, FixtureHandler.failures
        assert not errors, errors
        print("PASS: asset URLs, project subpath, canonical configuration")
        print("PASS: no JavaScript errors or missing fixture assets")
        print(f"Screenshots: {output}")
    finally:
        driver.quit()
        fixture.shutdown()
        fixture.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    check(parser.parse_args().url)
