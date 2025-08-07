#!/usr/bin/env python3
"""
Enhanced Dynamic Scraper for Ranch Data
Interacts with browser and extracts data dynamically
"""

import asyncio
import re
from typing import List, Dict, Any, Optional, Tuple
from playwright.async_api import async_playwright, Browser, Page
from .form_parser import FormParser
from .utils import normalize_string, clean_table_data, format_table_output, parse_profile_table


class DynamicScraper:
    """Dynamic scraper with runtime form detection and data extraction"""
    
    def __init__(self, base_url: str = "https://shorthorn.digitalbeef.com"):
        self.base_url = base_url
        self.form_parser = FormParser()
        self.browser = None
        self.playwright = None
        
    async def init_browser(self) -> Tuple[Browser, any]:
        """Initialize headless browser"""
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
        return browser, playwright
        
    async def navigate_to_site(self, page: Page) -> bool:
        """
        Navigate to the target website
        
        Args:
            page: Playwright page object
            
        Returns:
            True if successful, False otherwise
        """
        try:
            print(f"Navigating to {self.base_url}")
            await page.goto(self.base_url, wait_until='networkidle')
            return True
        except Exception as e:
            print(f"Error navigating to site: {e}")
            return False
    
    async def wait_for_form_ready(self, page: Page) -> bool:
        """
        Wait for the search form to be ready
        
        Args:
            page: Playwright page object
            
        Returns:
            True if form is ready, False otherwise
        """
        try:
            # Wait for the ranch search section
            await page.wait_for_selector('.blog li', timeout=10000)
            print("Ranch Search section loaded successfully")
            return True
        except Exception as e:
            print(f"Error waiting for form: {e}")
            return False
    
    async def validate_form_structure(self, page: Page) -> Tuple[bool, List[str]]:
        """
        Validate that all required form fields are present
        
        Args:
            page: Playwright page object
            
        Returns:
            Tuple of (is_valid, list_of_missing_fields)
        """
        return await self.form_parser.validate_required_fields(page)
    
    async def get_available_locations(self, page: Page) -> List[Dict[str, str]]:
        """
        Get all available location options
        
        Args:
            page: Playwright page object
            
        Returns:
            List of location options
        """
        return await self.form_parser.get_dropdown_options(page, 'search-member-location')
    
    async def fill_search_form(self, page: Page, search_params: Dict[str, str]) -> bool:
        """
        Fill the search form with provided parameters
        
        Args:
            page: Playwright page object
            search_params: Search parameters to fill
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get form structure
            form_structure = await self.form_parser.get_form_structure(page)
            
            for field_name, value in search_params.items():
                if not value:
                    continue
                    
                # Map field names to IDs
                field_mappings = {
                    'name': 'ranch_search_val',
                    'city': 'ranch_search_city',
                    'member_id': 'ranch_search_id',
                    'prefix': 'ranch_search_prefix',
                    'location': 'search-member-location'
                }
                
                field_id = field_mappings.get(field_name)
                if not field_id:
                    print(f"Unknown field: {field_name}")
                    continue
                
                try:
                    element = await page.wait_for_selector(f'#{field_id}', timeout=5000)
                    
                    if field_name == 'location':
                        # Handle location dropdown dynamically
                        mapped_value = await self.form_parser.map_location_input(page, value)
                        if mapped_value:
                            await element.select_option(value=mapped_value)
                            print(f"Selected location: {value} -> {mapped_value}")
                        else:
                            print(f"Warning: Could not map location '{value}'")
                    else:
                        # Handle text inputs
                        await element.fill(value.upper())
                        print(f"Filled {field_name}: {value}")
                        
                except Exception as e:
                    print(f"Error filling {field_name}: {e}")
                    return False
            
            return True
            
        except Exception as e:
            print(f"Error filling search form: {e}")
            return False
    
    async def trigger_search(self, page: Page) -> bool:
        """
        Trigger the search action
        
        Args:
            page: Playwright page object
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get search button info
            button_info = await self.form_parser.get_search_button_info(page)
            
            if button_info.get('hasFunction'):
                # Use JavaScript function if available
                await page.evaluate("doSearch_Ranch()")
            elif button_info.get('button'):
                # Use button click
                button_selector = button_info['button']['selector']
                await page.click(button_selector)
            else:
                # Fallback: look for search button
                search_button = await page.query_selector('input[name="btnsubmit"][value="Search..."]')
                if search_button:
                    await search_button.click()
                else:
                    print("Error: No search button found")
                    return False
            
            # Wait for search to complete
            await page.wait_for_timeout(2000)
            return True
            
        except Exception as e:
            print(f"Error triggering search: {e}")
            return False
    
    async def wait_for_results(self, page: Page) -> bool:
        """
        Wait for search results to appear
        
        Args:
            page: Playwright page object
            
        Returns:
            True if results found, False otherwise
        """
        try:
            # Wait for results container
            await page.wait_for_selector('#dvSearchResults', timeout=10000)
            
            # Wait a bit more for dynamic content
            await page.wait_for_timeout(3000)
            
            # Check if results are actually loaded
            content = await page.inner_text('#dvSearchResults')
            if content.strip():
                print("Search results loaded")
                return True
            else:
                print("Search results container is empty")
                return False
                
        except Exception as e:
            print(f"Error waiting for results: {e}")
            return False
    
    async def extract_table_data(self, page: Page) -> List[Dict[str, str]]:
        """
        Dynamically extract table data from results
        
        Args:
            page: Playwright page object
            
        Returns:
            List of dictionaries with extracted data
        """
        try:
            # Extract table structure and data dynamically
            table_data = await page.evaluate("""
                () => {
                    const resultsContainer = document.querySelector('#dvSearchResults');
                    if (!resultsContainer) return [];
                    
                    const rows = resultsContainer.querySelectorAll('tr');
                    const results = [];
                    
                    for (let i = 0; i < rows.length; i++) {
                        const cells = rows[i].querySelectorAll('td');
                        if (cells.length >= 3) {  // Minimum cells for valid data
                            // Skip header rows
                            const firstCell = cells[0] ? cells[0].textContent.trim() : '';
                            if (firstCell.includes('Profiles Match') || 
                                firstCell === 'Type' || 
                                firstCell === '') {
                                continue;
                            }
                            
                            // Extract data from cells
                            const rowData = {};
                            for (let j = 0; j < cells.length; j++) {
                                const cell = cells[j];
                                
                                // For member_id column (j === 1), preserve HTML to extract links
                                if (j === 1) {
                                    const innerHTML = cell.innerHTML.trim();
                                    rowData['member_id_html'] = innerHTML; // Keep HTML for enrichment
                                    rowData['member_id'] = cell.textContent.trim(); // Keep text for display
                                } else {
                                    const text = cell.textContent.trim();
                                    
                                    // Try to determine column type based on content
                                    if (j === 0) rowData['type'] = text;
                                    else if (j === 2) rowData['herd_prefix'] = text;
                                    else if (j === 3) rowData['member_name'] = text;
                                    else if (j === 4) rowData['dba'] = text;
                                    else if (j === 5) rowData['city'] = text;
                                    else if (j === 6) rowData['state'] = text;
                                    else rowData[`column_${j}`] = text;
                                }
                            }
                            
                            // Only add if we have meaningful data
                            if (rowData.type && rowData.type !== '') {
                                results.push(rowData);
                            }
                        }
                    }
                    
                    return results;
                }
            """)
            
            # Clean the data
            cleaned_data = clean_table_data(table_data)
            
            print(f"Found {len(cleaned_data)} ranch entries")
            return cleaned_data
            
        except Exception as e:
            print(f"Error extracting table data: {e}")
            return []
    
    async def scrape_ranches(self, search_params: Dict[str, str]) -> List[Dict[str, str]]:
        """
        Main scraping method
        
        Args:
            search_params: Search parameters
            
        Returns:
            List of ranch data
        """
        try:
            # Initialize browser
            self.browser, self.playwright = await self.init_browser()
            page = await self.browser.new_page()
            
            # Navigate to site
            if not await self.navigate_to_site(page):
                return []
            
            # Wait for form to be ready
            if not await self.wait_for_form_ready(page):
                return []
            
            # Validate form structure
            is_valid, missing_fields = await self.validate_form_structure(page)
            if not is_valid:
                print(f"Missing required fields: {missing_fields}")
                return []
            
            # Fill search form
            if not await self.fill_search_form(page, search_params):
                return []
            
            # Trigger search
            if not await self.trigger_search(page):
                return []
            
            # Wait for results
            if not await self.wait_for_results(page):
                return []
            
            # Extract data
            results = await self.extract_table_data(page)
            
            return results
            
        except Exception as e:
            print(f"Error during scraping: {e}")
            return []
        finally:
            if self.browser:
                try:
                    await self.browser.close()
                except Exception as e:
                    print(f"Warning: Error closing browser: {e}")
            if self.playwright:
                try:
                    await self.playwright.stop()
                except Exception as e:
                    print(f"Warning: Error stopping playwright: {e}")
    
    async def get_form_info(self, page: Page) -> Dict[str, Any]:
        """
        Get comprehensive form information
        
        Args:
            page: Playwright page object
            
        Returns:
            Dictionary with form information
        """
        try:
            # Navigate to site if not already there
            if page.url != self.base_url:
                await self.navigate_to_site(page)
                await self.wait_for_form_ready(page)
            
            # Get form structure
            form_structure = await self.form_parser.get_form_structure(page)
            
            # Get available locations
            locations = await self.get_available_locations(page)
            
            # Get search button info
            button_info = await self.form_parser.get_search_button_info(page)
            
            return {
                'form_structure': form_structure,
                'available_locations': locations,
                'search_button': button_info,
                'base_url': self.base_url
            }
            
        except Exception as e:
            print(f"Error getting form info: {e}")
            return {}
    
    def format_results(self, results: List[Dict[str, str]]) -> str:
        """
        Format results as a table
        
        Args:
            results: List of ranch data
            
        Returns:
            Formatted table string
        """
        return format_table_output(results)
    
    async def enrich_with_member_details(self, page: Page, ranch_results: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Enrich ranch results with member profile details
        
        Args:
            page: Playwright page object
            ranch_results: Original ranch search results
            
        Returns:
            Enriched results with profile details
        """
        if not ranch_results:
            return ranch_results
        
        print(f"\nEnriching {len(ranch_results)} results with member profile details...")
        
        enriched_results = []
        
        for i, ranch in enumerate(ranch_results, 1):
            print(f"Processing member {i}/{len(ranch_results)}...")
            print(f"  Available fields: {list(ranch.keys())}")
            
            # Extract member ID and profile URL
            member_id_html = ranch.get('member_id_html', ranch.get('member_id', ranch.get('Member ID', '')))
            print(f"  Member ID HTML: {member_id_html[:100]}...")  # Show first 100 chars
            if not member_id_html:
                print(f"  Skipping row {i}: No Member ID found")
                enriched_results.append(ranch)
                continue
            
            # Extract member ID text and URL from HTML
            member_id = ''
            profile_url = ''
            
            if '<a href=' in member_id_html:
                # Extract URL from the anchor tag
                url_match = re.search(r'href="([^"]+)"', member_id_html)
                if url_match:
                    profile_url = url_match.group(1)
                    # Decode HTML entities
                    profile_url = profile_url.replace('&amp;', '&')
                
                # Extract the member ID text from between <u> tags or anchor text
                text_match = re.search(r'<u>([^<]+)</u>', member_id_html)
                if text_match:
                    member_id = text_match.group(1).strip()
                else:
                    # Fallback: extract text from anchor tag
                    text_match = re.search(r'>([^<]+)</a>', member_id_html)
                    if text_match:
                        member_id = text_match.group(1).strip()
            else:
                # No link found, use the raw text as member ID
                member_id = member_id_html.strip()
                # Try to construct URL from member ID
                profile_url = f"https://shorthorn.digitalbeef.com/modules.php?op=modload&name=_ranch&file=_ranch&member_id={member_id}"
            
            if not profile_url:
                print(f"  Skipping row {i}: Could not extract profile URL")
                enriched_results.append(ranch)
                continue
            
            try:
                # Navigate to profile page
                print(f"  Navigating to: {profile_url}")
                await page.goto(profile_url, wait_until='networkidle', timeout=15000)
                
                # Parse profile details
                profile_details = await parse_profile_table(page)
                
                # Debug output
                print(f"  Extracted profile details: {profile_details}")
                
                # Merge profile details with ranch data
                enriched_ranch = ranch.copy()
                enriched_ranch.update(profile_details)
                
                # Remove the HTML field from final output
                if 'member_id_html' in enriched_ranch:
                    del enriched_ranch['member_id_html']
                
                enriched_results.append(enriched_ranch)
                print(f"  ✓ Enriched member {member_id} - Breeder: {profile_details.get('breeder_type', 'N/A')}, Profile: {profile_details.get('profile_type', 'N/A')}")
                
            except Exception as e:
                print(f"  ✗ Error processing member {member_id}: {e}")
                # Add empty profile fields if there's an error
                enriched_ranch = ranch.copy()
                enriched_ranch.update({
                    'breeder_type': '',
                    'profile_type': '',
                    'profile_id': '',
                    'profile_name': '',
                    'dba': '',
                    'herd_prefix': ''
                })
                enriched_results.append(enriched_ranch)
        
        print(f"Enrichment complete. {len(enriched_results)} results processed.")
        return enriched_results 