import asyncio
import sys
from typing import Dict, List, Tuple

# Ensure modules are importable when run from repo root
from ranch_scraper.scraper import DynamicScraper
from ranch_scraper.form_parser import FormParser
from animal_scraper.scraper import AnimalSearchScraper
from epd_scraper.scraper import EPDSearchScraper

PASS = 'PASS'
FAIL = 'FAIL'


class TestResult:
    def __init__(self, name: str):
        self.name = name
        self.status = PASS
        self.details: List[str] = []

    def ok(self, msg: str):
        self.details.append(msg)

    def error(self, msg: str):
        self.status = FAIL
        self.details.append(msg)

    def to_summary(self) -> str:
        header = f"[{self.status}] {self.name}"
        if not self.details:
            return header
        return header + "\n  - " + "\n  - ".join(self.details)


async def test_ranch_simple_search() -> TestResult:
    t = TestResult('Ranch: simple search returns rows')
    try:
        scraper = DynamicScraper()
        # Try multiple broad parameter sets to ensure at least one returns results
        candidates = [
            {'location': 'Texas'},
            {'location': 'United States|TX'},
            {'location': 'TX'},
            {'name': 'A*'},
            {'location': 'Texas', 'name': 'A*'},
        ]
        last_len = 0
        for params in candidates:
            results = await scraper.scrape_ranches(params)
            last_len = len(results) if isinstance(results, list) else 0
            if last_len > 0:
                t.ok(f"Params {params} -> {last_len} rows")
                # quick column check
                sample = results[0]
                expected_keys = {'type', 'member_id', 'member_name', 'city', 'state'}
                missing = [k for k in expected_keys if k not in sample]
                if missing:
                    t.error(f"Missing expected keys in first row: {missing}")
                else:
                    t.ok('First row contains expected keys')
                return t
        t.error(f'All tried parameter sets returned 0 rows (last len={last_len})')
        return t
    except Exception as e:
        t.error(f'Exception: {e}')
        return t


async def test_ranch_location_mapping() -> TestResult:
    t = TestResult('Ranch: location dropdown and mapping')
    try:
        scraper = DynamicScraper()
        browser, playwright = await scraper.init_browser()
        try:
            page = await browser.new_page()
            await scraper.navigate_to_site(page)
            await scraper.wait_for_form_ready(page)
            options = await scraper.get_available_locations(page)
            if not options:
                t.error('No locations found in dropdown')
                return t
            t.ok(f"Found {len(options)} location options")
            # Map common inputs
            mapped_tx_name = await scraper.form_parser.map_location_input(page, 'Texas')
            mapped_tx_code = await scraper.form_parser.map_location_input(page, 'TX')
            if not mapped_tx_name and not mapped_tx_code:
                t.error("Could not map 'Texas' or 'TX' to a dropdown value")
            else:
                t.ok(f"Mapped 'Texas' -> {mapped_tx_name} , 'TX' -> {mapped_tx_code}")
            return t
        finally:
            try:
                await browser.close()
            except Exception:
                pass
            try:
                await playwright.stop()
            except Exception:
                pass
    except Exception as e:
        t.error(f'Exception: {e}')
        return t


async def test_animal_search_by_name() -> TestResult:
    t = TestResult('Animal: search by name wildcard returns rows')
    try:
        scraper = AnimalSearchScraper()
        params = {'sex': '', 'field': 'animal_name', 'value': 'RED*'}
        results = await scraper.scrape_animals(params)
        if not isinstance(results, list):
            t.error('Expected results to be a list')
            return t
        if not results:
            t.error('Expected non-empty results for name wildcard RED*')
            return t
        t.ok(f"Received {len(results)} rows")
        sample = results[0]
        expected = {'registration', 'registration_url', 'name', 'birthdate'}
        missing = [k for k in expected if k not in sample]
        if missing:
            t.error(f"Missing expected keys in first row: {missing}")
        else:
            t.ok('First row contains expected keys')
        return t
    except Exception as e:
        t.error(f'Exception: {e}')
        return t


async def test_animal_detail_extraction() -> TestResult:
    t = TestResult('Animal: detail extraction from search result')
    try:
        base = AnimalSearchScraper()
        # Use a query likely to return rows; fallback once if needed
        queries = [
            {'sex': '', 'field': 'animal_name', 'value': 'RED*'},
            {'sex': '', 'field': 'animal_name', 'value': 'A*'},
        ]
        results = []
        for q in queries:
            results = await base.scrape_animals(q)
            if results:
                t.ok(f"Search {q} returned {len(results)} rows")
                break
        if not results:
            t.error('No animal search produced results; cannot test detail extraction')
            return t
        url = results[0].get('registration_url')
        if not url:
            t.error('First result missing registration_url')
            return t
        # Extract details on separate page instance
        base.browser, base.playwright = await base.init_browser()
        try:
            page = await base.browser.new_page()
            details = await base.extract_animal_detail(page, url)
            if not isinstance(details, dict):
                t.error('Details should be a dict')
            elif not details:
                t.error('Details are empty')
            else:
                some_keys = ['registration', 'name', 'sex', 'dob']
                present = [k for k in some_keys if k in details]
                if present:
                    t.ok(f"Extracted keys: {present}")
                else:
                    t.error('Expected identification fields not found in details')
            return t
        finally:
            try:
                await base.browser.close()
            except Exception:
                pass
            try:
                await base.playwright.stop()
            except Exception:
                pass
    except Exception as e:
        t.error(f'Exception: {e}')
        return t


async def test_epd_basic_search() -> TestResult:
    t = TestResult('EPD: search returns rows with broad settings')
    try:
        scraper = EPDSearchScraper()
        # Try several broad parameter sets to obtain some rows
        candidates = [
            {'sort_field': 'epd_ww', 'search_sex': ''},
            {'sort_field': 'epd_ww', 'search_sex': 'B'},
            {'weaning_weight_min': '0', 'sort_field': 'epd_ww', 'search_sex': ''},
            {'milk_min': '0', 'sort_field': 'epd_ww', 'search_sex': ''},
        ]
        for params in candidates:
            results = await scraper.scrape_epd(params)
            if isinstance(results, list) and len(results) > 0:
                t.ok(f"Params {params} -> {len(results)} rows")
                sample = results[0]
                basic_keys = {'registration', 'name'}
                missing = [k for k in basic_keys if k not in sample]
                if missing:
                    t.error(f"Missing expected keys in first row: {missing}")
                else:
                    t.ok('First row contains expected keys')
                return t
        t.error('All tried EPD parameter sets returned 0 rows')
        return t
    except Exception as e:
        t.error(f'Exception: {e}')
        return t


async def run_all_tests() -> Tuple[List[TestResult], int]:
    tests = [
        test_ranch_simple_search,
        test_ranch_location_mapping,
        test_animal_search_by_name,
        test_animal_detail_extraction,
        test_epd_basic_search,
    ]
    results: List[TestResult] = []
    failures = 0
    for test in tests:
        res = await test()
        results.append(res)
        if res.status == FAIL:
            failures += 1
    return results, failures


def main():
    print('Running DigitalBeef automated tests...')
    try:
        results, failures = asyncio.run(run_all_tests())
    except RuntimeError:
        # For environments with existing loop (e.g., notebooks)
        loop = asyncio.get_event_loop()
        results, failures = loop.run_until_complete(run_all_tests())
    print('\n=== Test Results ===')
    for r in results:
        print(r.to_summary())
    print('\nSummary: {} passed, {} failed'.format(len(results) - failures, failures))
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    main() 