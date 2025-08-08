import asyncio
import re
from typing import List, Dict, Any, Optional, Tuple
from playwright.async_api import async_playwright, Browser, Page
from .form_parser import FormParser
from .utils import normalize_string, clean_table_data, format_table_output, parse_profile_table

class DynamicScraper:

    def __init__(self, base_url: str='https://shorthorn.digitalbeef.com'):
        self.base_url = base_url
        self.form_parser = FormParser()
        self.browser = None
        self.playwright = None

    async def init_browser(self) -> Tuple[Browser, any]:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
        return (browser, playwright)

    async def navigate_to_site(self, page: Page) -> bool:
        try:
            print(f'Navigating to {self.base_url}')
            await page.goto(self.base_url, wait_until='networkidle')
            return True
        except Exception as e:
            print(f'Error navigating to site: {e}')
            return False

    async def wait_for_form_ready(self, page: Page) -> bool:
        try:
            await page.wait_for_selector('.blog li', timeout=10000)
            print('Ranch Search section loaded successfully')
            return True
        except Exception as e:
            print(f'Error waiting for form: {e}')
            return False

    async def validate_form_structure(self, page: Page) -> Tuple[bool, List[str]]:
        return await self.form_parser.validate_required_fields(page)

    async def get_available_locations(self, page: Page) -> List[Dict[str, str]]:
        return await self.form_parser.get_dropdown_options(page, 'search-member-location')

    async def fill_search_form(self, page: Page, search_params: Dict[str, str]) -> bool:
        try:
            form_structure = await self.form_parser.get_form_structure(page)
            for field_name, value in search_params.items():
                if not value:
                    continue
                field_mappings = {'name': 'ranch_search_val', 'city': 'ranch_search_city', 'member_id': 'ranch_search_id', 'prefix': 'ranch_search_prefix', 'location': 'search-member-location'}
                field_id = field_mappings.get(field_name)
                if not field_id:
                    print(f'Unknown field: {field_name}')
                    continue
                try:
                    element = await page.wait_for_selector(f'#{field_id}', timeout=5000)
                    if field_name == 'location':
                        mapped_value = await self.form_parser.map_location_input(page, value)
                        if mapped_value:
                            await element.select_option(value=mapped_value)
                            print(f'Selected location: {value} -> {mapped_value}')
                        else:
                            print(f"Warning: Could not map location '{value}'")
                    else:
                        await element.fill(value.upper())
                        print(f'Filled {field_name}: {value}')
                except Exception as e:
                    print(f'Error filling {field_name}: {e}')
                    return False
            return True
        except Exception as e:
            print(f'Error filling search form: {e}')
            return False

    async def trigger_search(self, page: Page) -> bool:
        try:
            button_info = await self.form_parser.get_search_button_info(page)
            if button_info.get('hasFunction'):
                await page.evaluate('doSearch_Ranch()')
            elif button_info.get('button'):
                button_selector = button_info['button']['selector']
                await page.click(button_selector)
            else:
                search_button = await page.query_selector('input[name="btnsubmit"][value="Search..."]')
                if search_button:
                    await search_button.click()
                else:
                    print('Error: No search button found')
                    return False
            await page.wait_for_timeout(2000)
            return True
        except Exception as e:
            print(f'Error triggering search: {e}')
            return False

    async def wait_for_results(self, page: Page) -> bool:
        try:
            await page.wait_for_selector('#dvSearchResults', timeout=10000)
            await page.wait_for_timeout(3000)
            content = await page.inner_text('#dvSearchResults')
            if content.strip():
                print('Search results loaded')
                return True
            else:
                print('Search results container is empty')
                return False
        except Exception as e:
            print(f'Error waiting for results: {e}')
            return False

    async def extract_table_data(self, page: Page) -> List[Dict[str, str]]:
        try:
            table_data = await page.evaluate("\n                () => {\n                    const resultsContainer = document.querySelector('#dvSearchResults');\n                    if (!resultsContainer) return [];\n                    \n                    const rows = resultsContainer.querySelectorAll('tr');\n                    const results = [];\n                    \n                    for (let i = 0; i < rows.length; i++) {\n                        const cells = rows[i].querySelectorAll('td');\n                        if (cells.length >= 3) {  // Minimum cells for valid data\n                            // Skip header rows\n                            const firstCell = cells[0] ? cells[0].textContent.trim() : '';\n                            if (firstCell.includes('Profiles Match') || \n                                firstCell === 'Type' || \n                                firstCell === '') {\n                                continue;\n                            }\n                            \n                            // Extract data from cells\n                            const rowData = {};\n                            for (let j = 0; j < cells.length; j++) {\n                                const cell = cells[j];\n                                \n                                // For member_id column (j === 1), preserve HTML to extract links\n                                if (j === 1) {\n                                    const innerHTML = cell.innerHTML.trim();\n                                    rowData['member_id_html'] = innerHTML; // Keep HTML for enrichment\n                                    rowData['member_id'] = cell.textContent.trim(); // Keep text for display\n                                } else {\n                                const text = cell.textContent.trim();\n                                \n                                // Try to determine column type based on content\n                                if (j === 0) rowData['type'] = text;\n                                else if (j === 2) rowData['herd_prefix'] = text;\n                                else if (j === 3) rowData['member_name'] = text;\n                                else if (j === 4) rowData['dba'] = text;\n                                else if (j === 5) rowData['city'] = text;\n                                else if (j === 6) rowData['state'] = text;\n                                else rowData[`column_${j}`] = text;\n                                }\n                            }\n                            \n                            // Only add if we have meaningful data\n                            if (rowData.type && rowData.type !== '') {\n                                results.push(rowData);\n                            }\n                        }\n                    }\n                    \n                    return results;\n                }\n            ")
            cleaned_data = clean_table_data(table_data)
            print(f'Found {len(cleaned_data)} ranch entries')
            return cleaned_data
        except Exception as e:
            print(f'Error extracting table data: {e}')
            return []

    async def scrape_ranches(self, search_params: Dict[str, str]) -> List[Dict[str, str]]:
        try:
            self.browser, self.playwright = await self.init_browser()
            page = await self.browser.new_page()
            if not await self.navigate_to_site(page):
                return []
            if not await self.wait_for_form_ready(page):
                return []
            is_valid, missing_fields = await self.validate_form_structure(page)
            if not is_valid:
                print(f'Missing required fields: {missing_fields}')
                return []
            if not await self.fill_search_form(page, search_params):
                return []
            if not await self.trigger_search(page):
                return []
            if not await self.wait_for_results(page):
                return []
            results = await self.extract_table_data(page)
            return results
        except Exception as e:
            print(f'Error during scraping: {e}')
            return []
        finally:
            if self.browser:
                try:
                    await self.browser.close()
                except Exception as e:
                    print(f'Warning: Error closing browser: {e}')
            if self.playwright:
                try:
                    await self.playwright.stop()
                except Exception as e:
                    print(f'Warning: Error stopping playwright: {e}')

    async def get_form_info(self, page: Page) -> Dict[str, Any]:
        try:
            if page.url != self.base_url:
                await self.navigate_to_site(page)
                await self.wait_for_form_ready(page)
            form_structure = await self.form_parser.get_form_structure(page)
            locations = await self.get_available_locations(page)
            button_info = await self.form_parser.get_search_button_info(page)
            return {'form_structure': form_structure, 'available_locations': locations, 'search_button': button_info, 'base_url': self.base_url}
        except Exception as e:
            print(f'Error getting form info: {e}')
            return {}

    def format_results(self, results: List[Dict[str, str]]) -> str:
        return format_table_output(results)

    async def enrich_with_member_details(self, page: Page, ranch_results: List[Dict[str, str]]) -> List[Dict[str, str]]:
        if not ranch_results:
            return ranch_results
        print(f'\nEnriching {len(ranch_results)} results with member profile details...')
        enriched_results = []
        for i, ranch in enumerate(ranch_results, 1):
            print(f'Processing member {i}/{len(ranch_results)}...')
            print(f'  Available fields: {list(ranch.keys())}')
            member_id_html = ranch.get('member_id_html', ranch.get('member_id', ranch.get('Member ID', '')))
            print(f'  Member ID HTML: {member_id_html[:100]}...')
            if not member_id_html:
                print(f'  Skipping row {i}: No Member ID found')
                enriched_results.append(ranch)
                continue
            member_id = ''
            profile_url = ''
            if '<a href=' in member_id_html:
                url_match = re.search('href="([^"]+)"', member_id_html)
                if url_match:
                    profile_url = url_match.group(1)
                    profile_url = profile_url.replace('&amp;', '&')
                text_match = re.search('<u>([^<]+)</u>', member_id_html)
                if text_match:
                    member_id = text_match.group(1).strip()
                else:
                    text_match = re.search('>([^<]+)</a>', member_id_html)
                    if text_match:
                        member_id = text_match.group(1).strip()
            else:
                member_id = member_id_html.strip()
                profile_url = f'https://shorthorn.digitalbeef.com/modules.php?op=modload&name=_ranch&file=_ranch&member_id={member_id}'
            if not profile_url:
                print(f'  Skipping row {i}: Could not extract profile URL')
                enriched_results.append(ranch)
                continue
            try:
                print(f'  Navigating to: {profile_url}')
                await page.goto(profile_url, wait_until='networkidle', timeout=15000)
                profile_details = await parse_profile_table(page)
                print(f'  Extracted profile details: {profile_details}')
                enriched_ranch = ranch.copy()
                enriched_ranch.update(profile_details)
                if 'member_id_html' in enriched_ranch:
                    del enriched_ranch['member_id_html']
                enriched_results.append(enriched_ranch)
                print(f"  ✓ Enriched member {member_id} - Breeder: {profile_details.get('breeder_type', 'N/A')}, Profile: {profile_details.get('profile_type', 'N/A')}")
            except Exception as e:
                print(f'  ✗ Error processing member {member_id}: {e}')
                enriched_ranch = ranch.copy()
                enriched_ranch.update({'breeder_type': '', 'profile_type': '', 'profile_id': '', 'profile_name': '', 'dba': '', 'herd_prefix': ''})
                enriched_results.append(enriched_ranch)
        print(f'Enrichment complete. {len(enriched_results)} results processed.')
        return enriched_results
