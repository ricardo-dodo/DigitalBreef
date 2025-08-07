#!/usr/bin/env python3
"""
EPD Scraper for Digital Beef
Handles EPD (Expected Progeny Differences) search functionality
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from playwright.async_api import async_playwright, Browser, Page
from .form_parser import EPDFormParser
from ranch_scraper.utils import clean_table_data, format_table_output


class EPDSearchScraper:
    """EPD search scraper with dynamic form handling"""
    
    def __init__(self, base_url: str = "https://shorthorn.digitalbeef.com"):
        self.base_url = base_url
        self.form_parser = EPDFormParser()
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
    
    async def wait_for_epd_form_ready(self, page: Page) -> bool:
        """
        Wait for the EPD search form to be ready
        
        Args:
            page: Playwright page object
            
        Returns:
            True if form is ready, False otherwise
        """
        try:
            # Wait for the EPD search section
            await page.wait_for_selector('#epd_search', timeout=10000)
            print("EPD Search form loaded successfully")
            return True
        except Exception as e:
            print(f"Error waiting for EPD form: {e}")
            return False
    
    async def validate_form_structure(self, page: Page) -> Tuple[bool, List[str]]:
        """
        Validate that all required EPD form fields are present
        
        Args:
            page: Playwright page object
            
        Returns:
            Tuple of (is_valid, list_of_missing_fields)
        """
        return await self.form_parser.validate_required_fields(page)
    
    async def fill_search_form(self, page: Page, search_params: Dict[str, str]) -> bool:
        """
        Fill the EPD search form with provided parameters
        
        Args:
            page: Playwright page object
            search_params: Search parameters to fill
            
        Returns:
            True if successful, False otherwise
        """
        try:
            print("Filling EPD search form...")
            
            # Use the form parser to fill the form
            success = await self.form_parser.fill_epd_form(page, search_params)
            
            if success:
                print("EPD search form filled successfully")
            else:
                print("Failed to fill EPD search form")
            
            return success
            
        except Exception as e:
            print(f"Error filling EPD search form: {e}")
            return False
    
    async def trigger_search(self, page: Page) -> bool:
        """
        Trigger the EPD search
        
        Args:
            page: Playwright page object
            
        Returns:
            True if successful, False otherwise
        """
        try:
            print("Triggering EPD search...")
            
            # Execute the JavaScript function directly
            await page.evaluate("doSearch_Epd();")
            
            print("EPD search triggered successfully")
            return True
            
        except Exception as e:
            print(f"Error triggering EPD search: {e}")
            return False
    
    async def wait_for_results(self, page: Page) -> bool:
        """
        Wait for EPD search results to load
        
        Args:
            page: Playwright page object
            
        Returns:
            True if results loaded, False otherwise
        """
        try:
            print("Waiting for EPD search results...")
            
            # Wait for either results or no results message
            max_wait_time = 120  # 2 minutes max
            check_interval = 2    # Check every 2 seconds
            elapsed_time = 0
            
            while elapsed_time < max_wait_time:
                # Check for EPD results rows
                has_results = await page.evaluate("""
                    () => {
                        const resultRows = document.querySelectorAll('tr[id^="tr_"]');
                        return resultRows.length > 0;
                    }
                """)
                
                if has_results:
                    print(f"EPD search results loaded successfully after {elapsed_time} seconds")
                    return True
                
                # Check for no results message or error
                no_results = await page.evaluate("""
                    () => {
                        const noResultsMsg = document.querySelector('.no-results, .no-data, .error');
                        const loadingMsg = document.querySelector('.loading, .processing');
                        return {
                            noResults: noResultsMsg !== null,
                            loading: loadingMsg !== null
                        };
                    }
                """)
                
                if no_results['noResults']:
                    print("No EPD results found")
                    return True
                
                if not no_results['loading']:
                    # If not loading anymore and no results, might be done
                    await page.wait_for_timeout(1000)
                    elapsed_time += 1
                    continue
                
                # Still loading, wait and check again
                await page.wait_for_timeout(check_interval * 1000)
                elapsed_time += check_interval
                
                # Show progress every 10 seconds
                if elapsed_time % 10 == 0:
                    print(f"Still waiting for results... ({elapsed_time}s elapsed)")
            
            print(f"Search timeout after {max_wait_time} seconds")
            return True  # Return True to continue processing
            
        except Exception as e:
            print(f"Error waiting for EPD results: {e}")
            return False
    
    async def extract_table_data(self, page: Page) -> List[Dict[str, str]]:
        """
        Extract EPD table data from results
        
        Args:
            page: Playwright page object
            
        Returns:
            List of EPD data dictionaries
        """
        try:
            # Extract EPD results data
            epd_data = await page.evaluate("""
                () => {
                    const results = [];
                    const rows = document.querySelectorAll('tr[id^="tr_"]');
                    
                    for (const row of rows) {
                        const animalData = {};
                        
                        // Extract animal registration and name from first cell
                        const firstCell = row.querySelector('td:first-child');
                        if (firstCell) {
                            const regLink = firstCell.querySelector('a');
                            if (regLink) {
                                animalData['registration'] = regLink.textContent.trim();
                                animalData['registration_url'] = regLink.href;
                            }
                            
                            // Extract tattoo and name from nested table
                            const nestedTable = firstCell.querySelector('table');
                            if (nestedTable) {
                                const tattooRow = nestedTable.querySelector('tr:nth-child(2) td');
                                if (tattooRow) {
                                    animalData['tattoo'] = tattooRow.textContent.trim();
                                }
                                
                                const nameRow = nestedTable.querySelector('tr:nth-child(3) td');
                                if (nameRow) {
                                    animalData['name'] = nameRow.textContent.trim();
                                }
                            }
                        }
                        
                        // Extract EPD values from cells with border-left:thin style
                        const epdCells = row.querySelectorAll('td[style*="border-left:thin"]');
                        const traits = ['CED', 'BW', 'WW', 'YW', 'MK', 'TM', 'CEM', 'ST', 'YG', 'CW', 'REA', 'FAT', 'MB', '$CEZ', '$BMI', '$CPI', '$F'];
                        
                        for (let i = 0; i < epdCells.length && i < traits.length; i++) {
                            const cell = epdCells[i];
                            const trait = traits[i];
                            
                            const nestedTable = cell.querySelector('table');
                            if (nestedTable) {
                                const rows = nestedTable.querySelectorAll('tr');
                                
                                if (rows.length >= 4) {
                                    // EPD value (first row)
                                    const epdValue = rows[0]?.querySelector('td')?.textContent.trim() || '';
                                    animalData[`${trait}_epd`] = epdValue;
                                    
                                    // Change value (second row)
                                    const changeValue = rows[1]?.querySelector('td')?.textContent.trim() || '';
                                    animalData[`${trait}_change`] = changeValue;
                                    
                                    // Accuracy (third row)
                                    const accuracy = rows[2]?.querySelector('td')?.textContent.trim() || '';
                                    animalData[`${trait}_acc`] = accuracy;
                                    
                                    // Rank (fourth row)
                                    const rank = rows[3]?.querySelector('td')?.textContent.trim() || '';
                                    animalData[`${trait}_rank`] = rank;
                                }
                            }
                        }
                        
                        if (Object.keys(animalData).length > 0) {
                            results.push(animalData);
                        }
                    }
                    
                    return results;
                }
            """)
            
            # Clean the data
            cleaned_data = clean_table_data(epd_data)
            
            print(f"Found {len(cleaned_data)} EPD entries")
            return cleaned_data
            
        except Exception as e:
            print(f"Error extracting EPD table data: {e}")
            return []
    
    async def scrape_epd(self, search_params: Dict[str, str]) -> List[Dict[str, str]]:
        """
        Main EPD scraping method
        
        Args:
            search_params: Search parameters
            
        Returns:
            List of EPD data
        """
        try:
            # Initialize browser
            self.browser, self.playwright = await self.init_browser()
            page = await self.browser.new_page()
            
            # Navigate to site
            if not await self.navigate_to_site(page):
                return []
            
            # Wait for EPD form to be ready
            if not await self.wait_for_epd_form_ready(page):
                return []
            
            # Validate form structure
            is_valid, missing_fields = await self.validate_form_structure(page)
            if not is_valid:
                print(f"Missing required EPD fields: {missing_fields}")
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
            print(f"Error during EPD scraping: {e}")
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
    
    def format_results(self, results: List[Dict[str, str]]) -> str:
        """
        Format EPD results for display with better organization
        
        Args:
            results: List of EPD result dictionaries
            
        Returns:
            Formatted string for display
        """
        if not results:
            return "No EPD results found."
        
        # Create a more organized display
        output = []
        output.append("=" * 80)
        output.append("EPD SEARCH RESULTS")
        output.append("=" * 80)
        output.append(f"Total Animals Found: {len(results)}")
        output.append("")
        
        for i, animal in enumerate(results, 1):
            output.append(f"Animal #{i}")
            output.append("-" * 40)
            
            # Animal Info
            output.append(f"Registration: {animal.get('registration', 'N/A')}")
            output.append(f"Tattoo: {animal.get('tattoo', 'N/A')}")
            output.append(f"Name: {animal.get('name', 'N/A')}")
            output.append("")
            
            # Growth & Maternal EPDs
            output.append("Growth & Maternal EPDs:")
            growth_traits = ['CED', 'BW', 'WW', 'YW', 'MK', 'TM', 'CEM', 'ST']
            for trait in growth_traits:
                epd = animal.get(f'{trait}_epd', 'N/A')
                change = animal.get(f'{trait}_change', 'N/A')
                acc = animal.get(f'{trait}_acc', 'N/A')
                rank = animal.get(f'{trait}_rank', 'N/A')
                output.append(f"  {trait:>3}: EPD={epd:>6} | Change={change:>6} | Acc={acc:>5} | Rank={rank:>4}")
            
            output.append("")
            
            # Carcass EPDs
            output.append("Carcass EPDs:")
            carcass_traits = ['YG', 'CW', 'REA', 'FAT', 'MB']
            for trait in carcass_traits:
                epd = animal.get(f'{trait}_epd', 'N/A')
                change = animal.get(f'{trait}_change', 'N/A')
                acc = animal.get(f'{trait}_acc', 'N/A')
                rank = animal.get(f'{trait}_rank', 'N/A')
                output.append(f"  {trait:>3}: EPD={epd:>6} | Change={change:>6} | Acc={acc:>5} | Rank={rank:>4}")
            
            output.append("")
            
            # Index EPDs
            output.append("Index EPDs:")
            index_traits = ['CEZ', 'BMI', 'CPI', 'F']
            for trait in index_traits:
                epd = animal.get(f'{trait}_epd', 'N/A')
                change = animal.get(f'{trait}_change', 'N/A')
                acc = animal.get(f'{trait}_acc', 'N/A')
                rank = animal.get(f'{trait}_rank', 'N/A')
                output.append(f"  {trait:>3}: EPD={epd:>6} | Change={change:>6} | Acc={acc:>5} | Rank={rank:>4}")
            
            output.append("")
            output.append("=" * 80)
            output.append("")
        
        return "\n".join(output)
    
    def format_results_table(self, results: List[Dict[str, str]]) -> str:
        """
        Format EPD results as a simple table
        
        Args:
            results: List of EPD result dictionaries
            
        Returns:
            Formatted table string
        """
        if not results:
            return "No EPD results found."
        
        return format_table_output(results)
    
    async def extract_animal_detail(self, page: Page, animal_url: str) -> Dict[str, str]:
        """
        Extract detailed animal information from animal detail page
        
        Args:
            page: Playwright page object
            animal_url: URL to animal detail page
            
        Returns:
            Dictionary containing animal details
        """
        try:
            print(f"Extracting animal details from: {animal_url}")
            
            # Navigate to animal detail page
            await page.goto(animal_url, wait_until='networkidle')
            
            # Wait for the main table to load
            await page.wait_for_selector('table[style*="min-width:850px"]', timeout=10000)
            
            # Extract animal details
            details = await page.evaluate("""
                () => {
                    const details = {};
                    
                    // Extract basic identification info
                    const rows = document.querySelectorAll('tr');
                    for (const row of rows) {
                        const cells = row.querySelectorAll('td');
                        if (cells.length >= 2) {
                            const label = cells[0]?.textContent?.trim();
                            const value = cells[1]?.textContent?.trim();
                            
                            if (label && value) {
                                if (label.includes('Sex:')) details.sex = value;
                                if (label.includes('Name:')) details.name = value;
                                if (label.includes('Registration:')) details.registration = value;
                                if (label.includes('International ID:')) details.international_id = value;
                                if (label.includes('EID:')) details.eid = value;
                                if (label.includes('Horn/Poll/Scur:')) details.horn_poll_scur = value;
                                if (label.includes('Shorthorn %:')) details.shorthorn_percent = value;
                                if (label.includes('COI:')) details.coi = value;
                                if (label.includes('Service Type:')) details.service_type = value;
                                if (label.includes('Status:')) details.status = value;
                                if (label.includes('Color:')) details.color = value;
                                if (label.includes('DOB:')) details.dob = value;
                                if (label.includes('Disposal:')) details.disposal = value;
                            }
                        }
                    }
                    
                    // Extract Sire and Dam info
                    const sireRow = Array.from(rows).find(row => 
                        row.textContent.includes('Sire:') || row.textContent.includes('Sire:&nbsp;')
                    );
                    if (sireRow) {
                        const sireLink = sireRow.querySelector('a');
                        if (sireLink) {
                            details.sire_registration = sireLink.textContent.trim();
                            details.sire_name = sireRow.textContent.split('&nbsp;').pop()?.trim() || '';
                        }
                    }
                    
                    const damRow = Array.from(rows).find(row => 
                        row.textContent.includes('Dam:') || row.textContent.includes('Dam:&nbsp;')
                    );
                    if (damRow) {
                        const damLink = damRow.querySelector('a');
                        if (damLink) {
                            details.dam_registration = damLink.textContent.trim();
                            details.dam_name = damRow.textContent.split('&nbsp;').pop()?.trim() || '';
                        }
                    }
                    
                    // Extract Breeder info
                    const breederRow = Array.from(rows).find(row => 
                        row.textContent.includes('Breeder:') || row.textContent.includes('Breeder:&nbsp;')
                    );
                    if (breederRow) {
                        const breederLink = breederRow.querySelector('a');
                        if (breederLink) {
                            details.breeder_id = breederLink.textContent.trim();
                            details.breeder_name = breederRow.textContent.split('(').pop()?.split(')')[0]?.trim() || '';
                        }
                    }
                    
                    // Extract Herd Prefix and Tattoo info
                    const herdPrefixRow = Array.from(rows).find(row => 
                        row.textContent.includes('Herd Prefix:') || row.textContent.includes('Tattoo')
                    );
                    if (herdPrefixRow) {
                        const text = herdPrefixRow.textContent;
                        const prefixMatch = text.match(/Herd Prefix:.*?Tattoo.*?:\s*([A-Z]+)\s*:\s*([A-Z0-9]+)/);
                        if (prefixMatch) {
                            details.herd_prefix = prefixMatch[1];
                            details.tattoo = prefixMatch[2];
                        }
                    }
                    
                    return details;
                }
            """)
            
            print(f"Extracted animal details for {details.get('registration', 'Unknown')}")
            return details
            
        except Exception as e:
            print(f"Error extracting animal details: {e}")
            return {}
    
    def format_animal_detail(self, details: Dict[str, str]) -> str:
        """
        Format animal details for display
        
        Args:
            details: Dictionary containing animal details
            
        Returns:
            Formatted string for display
        """
        if not details:
            return "No animal details found."
        
        output = []
        output.append("=" * 80)
        output.append("ANIMAL DETAILS")
        output.append("=" * 80)
        output.append("")
        
        # Basic Information
        output.append("BASIC INFORMATION:")
        output.append("-" * 30)
        output.append(f"Registration: {details.get('registration', 'N/A')}")
        output.append(f"Name: {details.get('name', 'N/A')}")
        output.append(f"Sex: {details.get('sex', 'N/A')}")
        output.append(f"Color: {details.get('color', 'N/A')}")
        output.append(f"International ID: {details.get('international_id', 'N/A')}")
        output.append(f"EID: {details.get('eid', 'N/A')}")
        output.append(f"Horn/Poll/Scur: {details.get('horn_poll_scur', 'N/A')}")
        output.append(f"Shorthorn %: {details.get('shorthorn_percent', 'N/A')}")
        output.append(f"COI: {details.get('coi', 'N/A')}")
        output.append("")
        
        # Herd Information
        output.append("HERD INFORMATION:")
        output.append("-" * 30)
        output.append(f"Herd Prefix: {details.get('herd_prefix', 'N/A')}")
        output.append(f"Tattoo: {details.get('tattoo', 'N/A')}")
        output.append("")
        
        # Parent Information
        output.append("PARENT INFORMATION:")
        output.append("-" * 30)
        output.append(f"Sire Registration: {details.get('sire_registration', 'N/A')}")
        output.append(f"Sire Name: {details.get('sire_name', 'N/A')}")
        output.append(f"Dam Registration: {details.get('dam_registration', 'N/A')}")
        output.append(f"Dam Name: {details.get('dam_name', 'N/A')}")
        output.append("")
        
        # Breeder Information
        output.append("BREEDER INFORMATION:")
        output.append("-" * 30)
        output.append(f"Breeder ID: {details.get('breeder_id', 'N/A')}")
        output.append(f"Breeder Name: {details.get('breeder_name', 'N/A')}")
        output.append("")
        
        # Dates and Status
        output.append("DATES AND STATUS:")
        output.append("-" * 30)
        output.append(f"Date of Birth: {details.get('dob', 'N/A')}")
        output.append(f"Disposal Date: {details.get('disposal', 'N/A')}")
        output.append(f"Service Type: {details.get('service_type', 'N/A')}")
        output.append(f"Status: {details.get('status', 'N/A')}")
        output.append("")
        output.append("=" * 80)
        
        return "\n".join(output) 