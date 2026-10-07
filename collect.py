"""Collect displayed outputs from Google's actual search widget; never simulate."""
import argparse
import csv
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = 'https://www.google.com/search?q=random+number+generator&hl=en'


def check_access(page):
    text = page.locator('body').inner_text(timeout=5000).lower()
    if '/sorry/' in page.url or 'unusual traffic' in text:
        raise RuntimeError('Google blocked automated access (unusual traffic/CAPTCHA). '
                           'See failure.png; try running locally with --headed.')


def find_generate_button(page):
    # Google can change internal IDs while retaining the visible button name.
    candidates = page.locator('#rng-button').or_(
        page.get_by_role('button', name=re.compile(r'^(generate|生成)$', re.I))
    ).filter(visible=True)
    candidates.first.wait_for(state='visible', timeout=30000)
    if candidates.count() != 1:
        raise RuntimeError('Multiple generation buttons found; refusing ambiguous sampling')
    return candidates


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--samples', type=int, default=10000)
    parser.add_argument('--delay-ms', type=int, default=1200)
    parser.add_argument('--headed', action='store_true')
    args = parser.parse_args()
    if not 1 <= args.samples <= 10000 or not 1200 <= args.delay_ms <= 10000:
        parser.error('samples must be 1..10000; delay-ms must be 1200..10000')
    output = Path('results')
    output.mkdir(exist_ok=True)
    metadata = dict(url=URL, requested=args.samples, completed=0, minimum=1,
                    maximum=41, delay_ms=args.delay_ms,
                    started=datetime.now(timezone.utc).isoformat(), status='running')
    with sync_playwright() as p:
        launch = dict(headless=not args.headed)
        if os.environ.get('CHROMIUM_EXECUTABLE'):
            launch['executable_path'] = os.environ['CHROMIUM_EXECUTABLE']
        browser = p.chromium.launch(**launch)
        page = browser.new_page(locale='en-US')
        try:
            response = page.goto(URL, wait_until='domcontentloaded', timeout=60000)
            metadata['http_status'] = response.status if response else None
            for label in ['Reject all', 'Accept all']:
                consent = page.get_by_role('button', name=label, exact=True)
                if consent.count() and consent.first.is_visible():
                    consent.first.click()
                    break
            check_access(page)
            minimum = page.locator('input#rng-min, #rng-min input')
            maximum = page.locator('input#rng-max, #rng-max input')
            button = find_generate_button(page)
            value = page.locator('#rng-value')

            def bounds(low, high):
                # Set maximum first so increasing the minimum cannot cross it.
                maximum.fill(str(high))
                maximum.press('Tab')
                minimum.fill(str(low))
                minimum.press('Tab')
                if minimum.input_value() != str(low) or maximum.input_value() != str(high):
                    raise RuntimeError('Range controls did not retain the requested bounds')

            def generate():
                button.click()
                page.wait_for_timeout(args.delay_ms)
                page.wait_for_function('''() => {
                  const el = document.querySelector('#rng-value');
                  return el && el.getAnimations({subtree:true}).every(a => a.playState !== 'running');
                }''', timeout=10000)
                text = value.inner_text().strip().replace(',', '')
                if not text.isdigit():
                    raise RuntimeError(f'Unexpected result text: {text!r}')
                return int(text)

            # Verify the widget handles clicks and range settings before sampling.
            for endpoint in [1, 41]:
                bounds(endpoint, endpoint)
                if generate() != endpoint:
                    raise RuntimeError('Widget self-check failed; no valid collection started')
            bounds(1, 41)
            with (output / 'samples.csv').open('w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['trial', 'value', 'utc'])
                for trial in range(1, args.samples + 1):
                    number = generate()
                    if not 1 <= number <= 41:
                        raise RuntimeError(f'Out-of-range result: {number}')
                    # Equal consecutive values are valid independent observations.
                    writer.writerow([trial, number, datetime.now(timezone.utc).isoformat()])
                    f.flush()
                    metadata['completed'] = trial
                    if trial % 100 == 0:
                        print(f'{trial}/{args.samples}', flush=True)
            metadata['status'] = 'complete'
        except Exception as exc:
            metadata['status'] = 'failed'
            metadata['error'] = str(exc)
            metadata['page_url'] = page.url
            # Save diagnostics independently: a failed screenshot must not hide text.
            diagnostics = [
                lambda: page.screenshot(path=str(output / 'failure.png'), full_page=True),
                lambda: (output / 'failure.html').write_text(page.content()),
                lambda: (output / 'failure.txt').write_text(
                    page.locator('body').inner_text(timeout=5000)),
            ]
            for save in diagnostics:
                try:
                    save()
                except Exception as diagnostic_error:
                    print(f'Diagnostic capture failed: {diagnostic_error}', flush=True)
            print(f'Collection failed at {page.url}: {exc}', flush=True)
            raise
        finally:
            metadata['finished'] = datetime.now(timezone.utc).isoformat()
            (output / 'metadata.json').write_text(json.dumps(metadata, indent=2))
            browser.close()


if __name__ == '__main__':
    main()
