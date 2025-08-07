#!/usr/bin/env python3
"""
Test cases for Dynamic Ranch Scraper
Validates runtime behavior and dynamic functionality
"""

import asyncio
import unittest
from unittest.mock import Mock, patch, AsyncMock
from typing import List, Dict, Any

from .form_parser import FormParser
from .scraper import DynamicScraper
from .exporter import DynamicExporter
from .utils import validate_search_params, clean_table_data, normalize_string


class TestFormParser(unittest.TestCase):
    """Test form parser functionality"""
    
    def setUp(self):
        self.parser = FormParser()
    
    def test_normalize_input(self):
        """Test input normalization"""
        # Test basic normalization
        self.assertEqual(self.parser.normalize_input("  Texas  "), "TEXAS")
        self.assertEqual(self.parser.normalize_input("tx"), "TEXAS")
        self.assertEqual(self.parser.normalize_input(""), "")
        
        # Test abbreviations
        self.assertEqual(self.parser.normalize_input("TX"), "TEXAS")
        self.assertEqual(self.parser.normalize_input("CA"), "CALIFORNIA")
    
    @patch('form_parser.Page')
    async def test_get_dropdown_options(self, mock_page):
        """Test dropdown options extraction"""
        # Mock page.evaluate response
        mock_page.evaluate.return_value = [
            {'value': 'United States|TX', 'text': 'United States - Texas'},
            {'value': 'United States|CA', 'text': 'United States - California'},
            {'value': 'Canada|AB', 'text': 'Canada - Alberta'}
        ]
        
        options = await self.parser.get_dropdown_options(mock_page, 'search-member-location')
        
        self.assertEqual(len(options), 3)
        self.assertEqual(options[0]['value'], 'United States|TX')
        self.assertEqual(options[0]['text'], 'United States - Texas')
    
    @patch('form_parser.Page')
    async def test_map_location_input(self, mock_page):
        """Test location input mapping"""
        # Mock dropdown options
        mock_options = [
            {'value': 'United States|TX', 'text': 'United States - Texas'},
            {'value': 'United States|CA', 'text': 'United States - California'}
        ]
        
        with patch.object(self.parser, 'get_dropdown_options', return_value=mock_options):
            # Test exact match
            result = await self.parser.map_location_input(mock_page, 'United States|TX')
            self.assertEqual(result, 'United States|TX')
            
            # Test text match
            result = await self.parser.map_location_input(mock_page, 'Texas')
            self.assertEqual(result, 'United States|TX')
            
            # Test no match
            result = await self.parser.map_location_input(mock_page, 'Invalid')
            self.assertIsNone(result)


class TestUtils(unittest.TestCase):
    """Test utility functions"""
    
    def test_validate_search_params(self):
        """Test search parameter validation"""
        # Valid parameters
        params = {'name': 'Test', 'city': 'Dallas'}
        is_valid, errors = validate_search_params(params)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        
        # Empty parameters
        params = {}
        is_valid, errors = validate_search_params(params)
        self.assertFalse(is_valid)
        self.assertIn("At least one search parameter must be provided", errors)
        
        # Invalid characters
        params = {'name': 'Test<script>'}
        is_valid, errors = validate_search_params(params)
        self.assertFalse(is_valid)
        self.assertIn("contains invalid characters", errors[0])
    
    def test_clean_table_data(self):
        """Test table data cleaning"""
        raw_data = [
            {'type': '  AA  ', 'member_id': '44-12345', 'city': '  Dallas  '},
            {'type': 'BB', 'member_id': '44-67890', 'city': 'Austin'}
        ]
        
        cleaned = clean_table_data(raw_data)
        
        self.assertEqual(len(cleaned), 2)
        self.assertEqual(cleaned[0]['type'], 'AA')
        self.assertEqual(cleaned[0]['city'], 'Dallas')
        self.assertEqual(cleaned[1]['type'], 'BB')
    
    def test_normalize_string(self):
        """Test string normalization"""
        self.assertEqual(normalize_string("  Texas  "), "TEXAS")
        self.assertEqual(normalize_string("tx"), "TEXAS")
        self.assertEqual(normalize_string(""), "")


class TestExporter(unittest.TestCase):
    """Test exporter functionality"""
    
    def setUp(self):
        self.exporter = DynamicExporter()
    
    def test_validate_export_format(self):
        """Test export format validation"""
        self.assertTrue(self.exporter.validate_export_format('csv'))
        self.assertTrue(self.exporter.validate_export_format('json'))
        self.assertFalse(self.exporter.validate_export_format('xml'))
        self.assertFalse(self.exporter.validate_export_format('invalid'))
    
    def test_get_export_info(self):
        """Test export info generation"""
        data = [
            {'type': 'AA', 'member_id': '44-12345', 'city': 'Dallas'},
            {'type': 'BB', 'member_id': '44-67890', 'city': 'Austin'}
        ]
        
        info = self.exporter.get_export_info(data)
        
        self.assertEqual(info['row_count'], 2)
        self.assertEqual(len(info['columns']), 3)
        self.assertTrue(info['exportable'])
        self.assertIn('type', info['columns'])
        self.assertIn('member_id', info['columns'])
        self.assertIn('city', info['columns'])


class TestDynamicScraper(unittest.TestCase):
    """Test dynamic scraper functionality"""
    
    def setUp(self):
        self.scraper = DynamicScraper()
    
    @patch('scraper.async_playwright')
    async def test_init_browser(self, mock_playwright):
        """Test browser initialization"""
        # Mock playwright
        mock_playwright_instance = Mock()
        mock_playwright_instance.start.return_value = mock_playwright_instance
        mock_playwright_instance.chromium.launch.return_value = Mock()
        mock_playwright.return_value = mock_playwright_instance
        
        browser, playwright = await self.scraper.init_browser()
        
        self.assertIsNotNone(browser)
        self.assertIsNotNone(playwright)
    
    def test_format_results(self):
        """Test results formatting"""
        results = [
            {'type': 'AA', 'member_id': '44-12345', 'city': 'Dallas'},
            {'type': 'BB', 'member_id': '44-67890', 'city': 'Austin'}
        ]
        
        formatted = self.scraper.format_results(results)
        
        self.assertIn('AA', formatted)
        self.assertIn('44-12345', formatted)
        self.assertIn('Dallas', formatted)
        self.assertIn('Total results: 2', formatted)


class TestIntegration(unittest.TestCase):
    """Integration tests"""
    
    @patch('scraper.DynamicScraper.scrape_ranches')
    async def test_end_to_end_workflow(self, mock_scrape):
        """Test end-to-end workflow"""
        # Mock scraper response
        mock_results = [
            {'type': 'AA', 'member_id': '44-12345', 'city': 'Dallas'},
            {'type': 'BB', 'member_id': '44-67890', 'city': 'Austin'}
        ]
        mock_scrape.return_value = mock_results
        
        scraper = DynamicScraper()
        exporter = DynamicExporter()
        
        # Test search parameters
        search_params = {'name': 'Test', 'location': 'Texas'}
        
        # Run scraper
        results = await scraper.scrape_ranches(search_params)
        
        # Verify results
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['type'], 'AA')
        
        # Test export
        export_file = exporter.export_data(results, 'csv')
        self.assertNotEqual(export_file, "")


# Async test runner
class AsyncTestCase(unittest.TestCase):
    """Base class for async tests"""
    
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def tearDown(self):
        self.loop.close()
    
    def run_async_test(self, coro):
        """Run an async test"""
        return self.loop.run_until_complete(coro)


# Test runner
def run_tests():
    """Run all tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestFormParser))
    suite.addTests(loader.loadTestsFromTestCase(TestUtils))
    suite.addTests(loader.loadTestsFromTestCase(TestExporter))
    suite.addTests(loader.loadTestsFromTestCase(TestDynamicScraper))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1) 