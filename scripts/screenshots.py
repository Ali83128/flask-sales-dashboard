"""Capture README screenshots from a running instance: python scripts/screenshots.py [base_url]"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5000"
OUT = Path(__file__).resolve().parent.parent / "docs" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1)

    page.goto(f"{BASE}/login")
    page.screenshot(path=OUT / "01-login.png")

    page.fill("input[name=email]", "demo@example.com")
    page.fill("input[name=password]", "demo1234")
    page.click("button[type=submit]")
    page.wait_for_url(f"{BASE}/")
    page.goto(f"{BASE}/?range=90d")
    page.wait_for_selector("body[data-charts-ready='1']")
    page.wait_for_timeout(400)
    page.screenshot(path=OUT / "02-dashboard.png")

    page.goto(f"{BASE}/orders/?q=&status=paid&region=West")
    page.screenshot(path=OUT / "03-orders-filtered.png")

    page.goto(f"{BASE}/products/")
    page.click("text=Edit >> nth=2")
    page.fill("input[name=price]", "-5")
    page.click("button:has-text('Save changes')")
    page.wait_for_selector(".field-error")
    page.screenshot(path=OUT / "04-product-edit.png")

    browser.close()
print(f"Saved screenshots to {OUT}")
