import asyncio
import unittest
from unittest.mock import Mock, patch, AsyncMock
from typing import List, Dict, Any
from .form_parser import FormParser
from .scraper import DynamicScraper
from .exporter import DynamicExporter
from .utils import validate_search_params, clean_table_data, normalize_string

class TestFormParser(unittest.TestCase):

    def setUp(self):
        self.parser = FormParser()

    def test_normalize_input(self):
        self.assertEqual(self.parser.normalize_input('  Texas  '), 'TEXAS')
        self.assertEqual(self.parser.normalize_input('tx'), 'TEXAS')
        self.assertEqual(self.parser.normalize_input(''), '')
        self.assertEqual(self.parser.normalize_input('TX'), 'TEXAS')
        self.assertEqual(self.parser.normalize_input('CA'), 'CALIFORNIA')

    @patch('form_parser.Page')
    async def test_get_dropdown_options(self, mock_page):
        mock_page.evaluate.return_value = [{'value': 'United States|TX', 'text': 'United States - Texas'}, {'value': 'United States|CA', 'text': 'United States - California'}, {'value': 'Canada|AB', 'text': 'Canada - Alberta'}]
        options = await self.parser.get_dropdown_options(mock_page, 'search-member-location')
        self.assertEqual(len(options), 3)
        self.assertEqual(options[0]['value'], 'United States|TX')
        self.assertEqual(options[0]['text'], 'United States - Texas')

    @patch('form_parser.Page')
    async def test_map_location_input(self, mock_page):
        mock_options = [{'value': 'United States|TX', 'text': 'United States - Texas'}, {'value': 'United States|CA', 'text': 'United States - California'}]
        with patch.object(self.parser, 'get_dropdown_options', return_value=mock_options):
            result = await self.parser.map_location_input(mock_page, 'United States|TX')
            self.assertEqual(result, 'United States|TX')
            result = await self.parser.map_location_input(mock_page, 'Texas')
            self.assertEqual(result, 'United States|TX')
            result = await self.parser.map_location_input(mock_page, 'Invalid')
            self.assertIsNone(result)

class TestUtils(unittest.TestCase):

    def test_validate_search_params(self):
        params = {'name': 'Test', 'city': 'Dallas'}
        is_valid, errors = validate_search_params(params)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        params = {}
        is_valid, errors = validate_search_params(params)
        self.assertFalse(is_valid)
        self.assertIn('At least one search parameter must be provided', errors)
        params = {'name': 'Test<script>'}
        is_valid, errors = validate_search_params(params)
        self.assertFalse(is_valid)
        self.assertIn('contains invalid characters', errors[0])

    def test_clean_table_data(self):
        raw_data = [{'type': '  AA  ', 'member_id': '44-12345', 'city': '  Dallas  '}, {'type': 'BB', 'member_id': '44-67890', 'city': 'Austin'}]
        cleaned = clean_table_data(raw_data)
        self.assertEqual(len(cleaned), 2)
        self.assertEqual(cleaned[0]['type'], 'AA')
        self.assertEqual(cleaned[0]['city'], 'Dallas')
        self.assertEqual(cleaned[1]['type'], 'BB')

    def test_normalize_string(self):
        self.assertEqual(normalize_string('  Texas  '), 'TEXAS')
        self.assertEqual(normalize_string('tx'), 'TEXAS')
        self.assertEqual(normalize_string(''), '')

class TestExporter(unittest.TestCase):

    def setUp(self):
        self.exporter = DynamicExporter()

    def test_validate_export_format(self):
        self.assertTrue(self.exporter.validate_export_format('csv'))
        self.assertTrue(self.exporter.validate_export_format('json'))
        self.assertFalse(self.exporter.validate_export_format('xml'))
        self.assertFalse(self.exporter.validate_export_format('invalid'))

    def test_get_export_info(self):
        data = [{'type': 'AA', 'member_id': '44-12345', 'city': 'Dallas'}, {'type': 'BB', 'member_id': '44-67890', 'city': 'Austin'}]
        info = self.exporter.get_export_info(data)
        self.assertEqual(info['row_count'], 2)
        self.assertEqual(len(info['columns']), 3)
        self.assertTrue(info['exportable'])
        self.assertIn('type', info['columns'])
        self.assertIn('member_id', info['columns'])
        self.assertIn('city', info['columns'])

class TestDynamicScraper(unittest.TestCase):

    def setUp(self):
        self.scraper = DynamicScraper()

    @patch('scraper.async_playwright')
    async def test_init_browser(self, mock_playwright):
        mock_playwright_instance = Mock()
        mock_playwright_instance.start.return_value = mock_playwright_instance
        mock_playwright_instance.chromium.launch.return_value = Mock()
        mock_playwright.return_value = mock_playwright_instance
        browser, playwright = await self.scraper.init_browser()
        self.assertIsNotNone(browser)
        self.assertIsNotNone(playwright)

    def test_format_results(self):
        results = [{'type': 'AA', 'member_id': '44-12345', 'city': 'Dallas'}, {'type': 'BB', 'member_id': '44-67890', 'city': 'Austin'}]
        formatted = self.scraper.format_results(results)
        self.assertIn('AA', formatted)
        self.assertIn('44-12345', formatted)
        self.assertIn('Dallas', formatted)
        self.assertIn('Total results: 2', formatted)

class TestIntegration(unittest.TestCase):

    @patch('scraper.DynamicScraper.scrape_ranches')
    async def test_end_to_end_workflow(self, mock_scrape):
        mock_results = [{'type': 'AA', 'member_id': '44-12345', 'city': 'Dallas'}, {'type': 'BB', 'member_id': '44-67890', 'city': 'Austin'}]
        mock_scrape.return_value = mock_results
        scraper = DynamicScraper()
        exporter = DynamicExporter()
        search_params = {'name': 'Test', 'location': 'Texas'}
        results = await scraper.scrape_ranches(search_params)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['type'], 'AA')
        export_file = exporter.export_data(results, 'csv')
        self.assertNotEqual(export_file, '')

class AsyncTestCase(unittest.TestCase):

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def run_async_test(self, coro):
        return self.loop.run_until_complete(coro)

def run_tests():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestFormParser))
    suite.addTests(loader.loadTestsFromTestCase(TestUtils))
    suite.addTests(loader.loadTestsFromTestCase(TestExporter))
    suite.addTests(loader.loadTestsFromTestCase(TestDynamicScraper))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()
if __name__ == '__main__':
    success = run_tests()
    exit(0 if success else 1)
