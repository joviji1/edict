#!/usr/bin/env python3
"""Take all dashboard screenshots for the README using Playwright."""
from playwright.sync_api import sync_playwright
import os

SHOTS = os.path.join(os.path.dirname(__file__), '..', 'docs', 'screenshots')
URL = 'http://localhost:7891'

SHOTS_PLAN = [
    ('01-kanban-main.png', '📋 01 kanban...', 'edicts', 800),
    ('02-approval-panel.png', '🛡️ 02 approval...', 'approval', 1000),
    ('03-court-discussion.png', '🏛️ 03 court...', 'court', 1000),
    ('04-monitor.png', '🔭 04 monitor...', 'monitor', 800),
    ('05-relay-archive.png', '🚀 05 relay...', 'relay', 1000),
    ('06-task-detail.png', '📜 06 task detail...', 'edicts', 500),
    ('07-model-config.png', '⚙️ 07 models...', 'models', 1000),
    ('08-skills-config.png', '🛠️ 08 skills...', 'skills', 1000),
    ('09-official-overview.png', '👥 09 officials...', 'officials', 1000),
    ('10-sessions.png', '💬 10 sessions...', 'sessions', 800),
    ('11-memorials.png', '📜 11 memorials...', 'memorials', 800),
    ('12-templates.png', '📋 12 templates...', 'templates', 800),
    ('13-morning-briefing.png', '📰 13 morning...', 'morning', 1000),
]


def click_tab(page, key: str, wait_ms: int = 800):
    page.click(f'[data-tab="{key}"]')
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(wait_ms)


def main():
    os.makedirs(SHOTS, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            device_scale_factor=2,
            color_scheme='dark',
        )
        page = ctx.new_page()

        # ── Clear ceremony localStorage so it doesn't show on every load
        page.goto(URL)
        page.evaluate("localStorage.setItem('openclaw_court_date', new Date().toISOString().substring(0,10))")
        page.reload()
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(2000)

        for filename, message, tab_key, wait_ms in SHOTS_PLAN:
            print(message)
            click_tab(page, tab_key, wait_ms)
            if filename == '06-task-detail.png':
                cards = page.locator('.edict-card')
                if cards.count() > 0:
                    cards.first.click()
                    page.wait_for_timeout(800)
                    page.screenshot(path=os.path.join(SHOTS, filename), full_page=False)
                    page.keyboard.press('Escape')
                    page.wait_for_timeout(300)
                else:
                    print('⚠️ no edict card found, skip 06-task-detail.png')
                continue
            page.screenshot(path=os.path.join(SHOTS, filename), full_page=False)

        # 14. Ceremony - clear date then reload
        print('🎬 14 ceremony...')
        page.evaluate("localStorage.removeItem('openclaw_court_date')")
        page.reload()
        page.wait_for_timeout(2500)
        page.screenshot(path=os.path.join(SHOTS, '14-ceremony.png'), full_page=False)

        browser.close()
    print('✅ All screenshots saved to', SHOTS)


if __name__ == '__main__':
    main()
