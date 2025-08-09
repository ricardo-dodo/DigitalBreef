from typing import List, Dict, Tuple, Any
from playwright.async_api import async_playwright, Browser, Page
from .form_parser import AnimalFormParser
from ranch_scraper.utils import clean_table_data, format_table_output

class AnimalSearchScraper:

    def __init__(self, base_url: str='https://shorthorn.digitalbeef.com'):
        self.base_url = base_url
        self.form_parser = AnimalFormParser()
        self.browser: Browser | None = None
        self.playwright = None

    async def init_browser(self) -> Tuple[Browser, Any]:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
        return (browser, playwright)

    async def navigate_to_site(self, page: Page) -> bool:
        try:
            await page.goto(self.base_url, wait_until='networkidle')
            return True
        except Exception as e:
            print(f'Error navigating to site: {e}')
            return False

    async def wait_for_form_ready(self, page: Page) -> bool:
        try:
            await page.wait_for_selector('#tbl_animal_search', timeout=10000)
            return True
        except Exception as e:
            print(f'Error waiting for Animal form: {e}')
            return False

    async def scrape_animals(self, params: Dict[str, str]) -> List[Dict[str, str]]:
        try:
            self.browser, self.playwright = await self.init_browser()
            page = await self.browser.new_page()
            if not await self.navigate_to_site(page):
                return []
            if not await self.wait_for_form_ready(page):
                return []
            valid, missing = await self.form_parser.validate_required_fields(page)
            if not valid:
                print(f'Missing required fields: {missing}')
                return []
            await self.form_parser.ensure_form_defaults(page)
            if not await self.form_parser.fill_form(page, params):
                return []
            if not await self.form_parser.trigger_search(page):
                return []
            if not await self._wait_for_results(page):
                return []
            data = await self._extract_results(page)
            return data
        except Exception as e:
            print(f'Error during Animal scraping: {e}')
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

    async def _wait_for_results(self, page: Page) -> bool:
        try:
            # Wait until results container appears and has rows
            for _ in range(60):
                has_container = await page.evaluate("""
                    () => !!document.querySelector('#dvSearchResults')
                """)
                if has_container:
                    has_rows = await page.evaluate("""
                        () => document.querySelectorAll('#dvSearchResults tr[id^="tr_"]').length > 0
                    """)
                    if has_rows:
                        return True
                await page.wait_for_timeout(500)
            return False
        except Exception as e:
            print(f'Error waiting for Animal results: {e}')
            return False

    async def _extract_results(self, page: Page) -> List[Dict[str, str]]:
        try:
            results = await page.evaluate(
                """
                () => {
                                         const container = document.querySelector('#dvSearchResults');
                     const rows = container ? container.querySelectorAll('tr[id^="tr_"]') : [];
                     const out = [];
                     for (const row of rows) {
                        const cells = row.querySelectorAll('td');
                        if (!cells || cells.length < 4) continue;
                        const regCell = cells[0];
                        const prefixTattooCell = cells[1];
                        const nameCell = cells[2];
                        const dobCell = cells[3];

                        const regLink = regCell.querySelector('a');
                        const reg = regLink ? regLink.textContent.trim() : regCell.textContent.trim();
                        const regUrl = regLink ? regLink.href : '';
                        // Ensure we have a valid URL - if href is empty or malformed, skip this row
                        if (!regUrl || regUrl === '#' || regUrl.includes('javascript:')) {
                            continue;
                        }

                        const prefixTattoo = prefixTattooCell.textContent.trim();
                        const name = nameCell.textContent.trim();
                        const birthdate = dobCell.textContent.trim();

                        const rowData = {
                            registration: reg,
                            registration_url: regUrl,
                            prefix_tattoo: prefixTattoo,
                            name: name,
                            birthdate: birthdate,
                        };
                        out.push(rowData);
                    }
                    return out;
                }
                """
            )
            return clean_table_data(results)
        except Exception as e:
            print(f'Error extracting Animal table data: {e}')
            return []

    def format_results(self, results: List[Dict[str, str]]) -> str:
        if not results:
            return 'No animal results found.'
        return format_table_output(results)

    async def extract_animal_detail(self, page: Page, animal_url: str) -> Dict[str, str]:
        try:
            await page.goto(animal_url, wait_until='networkidle')
            
            # Wait for the main detail table to load with multiple fallback selectors
            try:
                await page.wait_for_selector('table[style*="min-width:850px"]', timeout=10000)
            except:
                try:
                    await page.wait_for_selector('table[border="1"]', timeout=5000)
                except:
                    await page.wait_for_selector('table', timeout=5000)
            
            details = await page.evaluate(
                """
                () => {
                    const details = {};
                    
                    // Find the main detail table first - try multiple selectors
                    let mainTable = document.querySelector('table[style*="min-width:850px"]');
                    if (!mainTable) {
                        mainTable = document.querySelector('table[border="1"]');
                    }
                    if (!mainTable) {
                        mainTable = document.querySelector('table');
                    }
                    if (!mainTable) return details;
                    
                    // Extract basic identification info from the main table
                    const rows = mainTable.querySelectorAll('tr');
                    for (const row of rows) {
                        const cells = row.querySelectorAll('td');
                        if (cells.length >= 2) {
                            const label = cells[0]?.textContent?.trim();
                            const value = cells[1]?.textContent?.trim();
                            
                            if (label && value && !label.includes('Identification') && !label.includes('Other Details')) {
                                if (label.includes('Sex:')) details.sex = value;
                                if (label.includes('Name:')) details.name = value;
                                if (label.includes('Registration:')) details.registration = value.replace('*x', '').trim();
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
                    
                    // Extract Sire and Dam info from the main table
                    const sireRow = Array.from(rows).find(row => 
                        row.textContent.includes('Sire:') && !row.textContent.includes('Identification')
                    );
                    if (sireRow) {
                        const sireLink = sireRow.querySelector('a');
                        if (sireLink) {
                            details.sire_registration = sireLink.textContent.trim().replace('*x', '');
                        }
                        // Extract sire name from the text content
                        const sireText = sireRow.textContent;
                        const sireNameMatch = sireText.match(/Sire:.*?([A-Z][A-Z\\s]+)$/);
                        if (sireNameMatch) {
                            details.sire_name = sireNameMatch[1].trim();
                        } else {
                            // Try alternative pattern for sire name
                            const altSireMatch = sireText.match(/Sire:.*?([A-Z][A-Z\\s]+[A-Z])/);
                            if (altSireMatch) details.sire_name = altSireMatch[1].trim();
                        }
                    }
                    
                    const damRow = Array.from(rows).find(row => 
                        row.textContent.includes('Dam:') && !row.textContent.includes('Identification')
                    );
                    if (damRow) {
                        const damLink = damRow.querySelector('a');
                        if (damLink) {
                            details.dam_registration = damLink.textContent.trim().replace('*x', '');
                        }
                        // Extract dam name from the text content
                        const damText = damRow.textContent;
                        const damNameMatch = damText.match(/Dam:.*?([A-Z][A-Z\\s]+)$/);
                        if (damNameMatch) {
                            details.dam_name = damNameMatch[1].trim();
                        } else {
                            // Try alternative pattern for dam name
                            const altDamMatch = damText.match(/Dam:.*?([A-Z][A-Z\\s]+[A-Z])/);
                            if (altDamMatch) details.dam_name = altDamMatch[1].trim();
                        }
                    }
                    
                    // Extract Breeder info from the main table
                    const breederRow = Array.from(rows).find(row => 
                        row.textContent.includes('Breeder:') && !row.textContent.includes('Identification')
                    );
                    if (breederRow) {
                        const breederLink = breederRow.querySelector('a');
                        if (breederLink) {
                            details.breeder_id = breederLink.textContent.trim();
                            const breederText = breederRow.textContent;
                            const breederNameMatch = breederText.match(/\\(([^)]+)\\)/);
                            if (breederNameMatch) details.breeder_name = breederNameMatch[1].trim();
                        }
                    }
                    
                    // Extract Herd Prefix and Tattoo info from nested table
                    const herdPrefixRow = Array.from(rows).find(row => 
                        row.textContent.includes('Herd Prefix:') && !row.textContent.includes('Identification')
                    );
                    if (herdPrefixRow) {
                        const nestedTable = herdPrefixRow.querySelector('table');
                        if (nestedTable) {
                            const nestedRows = nestedTable.querySelectorAll('tr');
                            for (const nrow of nestedRows) {
                                const ntext = nrow.textContent || '';
                                if (ntext.includes('Herd Prefix:')) {
                                    const prefixMatch = ntext.match(/Herd Prefix:\\s*([A-Z]+)/i);
                                    if (prefixMatch) details.herd_prefix = prefixMatch[1];
                                }
                                if (ntext.includes('Tattoo')) {
                                    const tattooMatch = ntext.match(/Tattoo.*?:\\s*([A-Z0-9]+)/i);
                                    if (tattooMatch) details.tattoo = tattooMatch[1];
                                }
                            }
                        }
                    }
                    
                    return details;
                }
                """
            )
            
            # If no details were extracted, try alternative selectors
            if not details or len(details) == 0:
                details = await page.evaluate(
                    """
                    () => {
                        const details = {};
                        
                        // Try to find any table with animal information
                        const tables = document.querySelectorAll('table');
                        for (const table of tables) {
                            const rows = table.querySelectorAll('tr');
                            for (const row of rows) {
                                const cells = row.querySelectorAll('td');
                                if (cells.length >= 2) {
                                    const text = row.textContent || '';
                                    
                                    // Extract basic info
                                    if (text.includes('Sex:')) {
                                        const match = text.match(/Sex:\s*([^\\n]+)/);
                                        if (match) details.sex = match[1].trim();
                                    }
                                    if (text.includes('Name:')) {
                                        const match = text.match(/Name:\s*([^\\n]+)/);
                                        if (match) details.name = match[1].trim();
                                    }
                                    if (text.includes('Registration:')) {
                                        const match = text.match(/Registration:\s*([^\\n]+)/);
                                        if (match) details.registration = match[1].replace('*x', '').trim();
                                    }
                                    if (text.includes('International ID:')) {
                                        const match = text.match(/International ID:\s*([^\\n]+)/);
                                        if (match) details.international_id = match[1].trim();
                                    }
                                    if (text.includes('EID:')) {
                                        const match = text.match(/EID:\s*([^\\n]+)/);
                                        if (match) details.eid = match[1].trim();
                                    }
                                    if (text.includes('Horn/Poll/Scur:')) {
                                        const match = text.match(/Horn\\/Poll\\/Scur:\s*([^\\n]+)/);
                                        if (match) details.horn_poll_scur = match[1].trim();
                                    }
                                    if (text.includes('Shorthorn %:')) {
                                        const match = text.match(/Shorthorn %:\s*([^\\n]+)/);
                                        if (match) details.shorthorn_percent = match[1].trim();
                                    }
                                    if (text.includes('COI:')) {
                                        const match = text.match(/COI:\s*([^\\n]+)/);
                                        if (match) details.coi = match[1].trim();
                                    }
                                    if (text.includes('Service Type:')) {
                                        const match = text.match(/Service Type:\s*([^\\n]+)/);
                                        if (match) details.service_type = match[1].trim();
                                    }
                                    if (text.includes('Status:')) {
                                        const match = text.match(/Status:\s*([^\\n]+)/);
                                        if (match) details.status = match[1].trim();
                                    }
                                    if (text.includes('Color:')) {
                                        const match = text.match(/Color:\s*([^\\n]+)/);
                                        if (match) details.color = match[1].trim();
                                    }
                                    if (text.includes('DOB:')) {
                                        const match = text.match(/DOB:\s*([^\\n]+)/);
                                        if (match) details.dob = match[1].trim();
                                    }
                                    if (text.includes('Disposal:')) {
                                        const match = text.match(/Disposal:\s*([^\\n]+)/);
                                        if (match) details.disposal = match[1].trim();
                                    }
                                    
                                    // Extract Sire and Dam info
                                    if (text.includes('Sire:')) {
                                        const sireLink = row.querySelector('a');
                                        if (sireLink) {
                                            details.sire_registration = sireLink.textContent.trim().replace('*x', '');
                                        }
                                        const sireNameMatch = text.match(/Sire:.*?([A-Z][A-Z\\s]+)$/);
                                        if (sireNameMatch) details.sire_name = sireNameMatch[1].trim();
                                    }
                                    
                                    if (text.includes('Dam:')) {
                                        const damLink = row.querySelector('a');
                                        if (damLink) {
                                            details.dam_registration = damLink.textContent.trim().replace('*x', '');
                                        }
                                        const damNameMatch = text.match(/Dam:.*?([A-Z][A-Z\\s]+)$/);
                                        if (damNameMatch) details.dam_name = damNameMatch[1].trim();
                                    }
                                    
                                    // Extract Breeder info
                                    if (text.includes('Breeder:')) {
                                        const breederLink = row.querySelector('a');
                                        if (breederLink) {
                                            details.breeder_id = breederLink.textContent.trim();
                                        }
                                        const breederNameMatch = text.match(/\\(([^)]+)\\)/);
                                        if (breederNameMatch) details.breeder_name = breederNameMatch[1].trim();
                                    }
                                    
                                    // Extract Herd Prefix and Tattoo
                                    if (text.includes('Herd Prefix:')) {
                                        const prefixMatch = text.match(/Herd Prefix:\s*([A-Z]+)/i);
                                        if (prefixMatch) details.herd_prefix = prefixMatch[1];
                                    }
                                    if (text.includes('Tattoo')) {
                                        const tattooMatch = text.match(/Tattoo.*?:\\s*([A-Z0-9]+)/i);
                                        if (tattooMatch) details.tattoo = tattooMatch[1];
                                    }
                                }
                            }
                        }
                        
                        return details;
                    }
                    """
                )
            
            return details if details else {}
        except Exception as e:
            print(f'Error extracting animal details: {e}')
            return {}

    def format_animal_detail(self, details: Dict[str, str]) -> str:
        if not details:
            return 'No animal details found.'
        output = []
        output.append('=' * 80)
        output.append('ANIMAL DETAILS')
        output.append('=' * 80)
        output.append('')
        output.append('BASIC INFORMATION:')
        output.append('-' * 30)
        output.append(f"Registration: {details.get('registration', 'N/A')}")
        output.append(f"Name: {details.get('name', 'N/A')}")
        output.append(f"Sex: {details.get('sex', 'N/A')}")
        output.append(f"Color: {details.get('color', 'N/A')}")
        output.append(f"International ID: {details.get('international_id', 'N/A')}")
        output.append(f"EID: {details.get('eid', 'N/A')}")
        output.append(f"Horn/Poll/Scur: {details.get('horn_poll_scur', 'N/A')}")
        output.append(f"Shorthorn %: {details.get('shorthorn_percent', 'N/A')}")
        output.append(f"COI: {details.get('coi', 'N/A')}")
        output.append('')
        output.append('HERD INFORMATION:')
        output.append('-' * 30)
        output.append(f"Herd Prefix: {details.get('herd_prefix', 'N/A')}")
        output.append(f"Tattoo: {details.get('tattoo', 'N/A')}")
        output.append('')
        output.append('PARENT INFORMATION:')
        output.append('-' * 30)
        output.append(f"Sire Registration: {details.get('sire_registration', 'N/A')}")
        output.append(f"Sire Name: {details.get('sire_name', 'N/A')}")
        output.append(f"Dam Registration: {details.get('dam_registration', 'N/A')}")
        output.append(f"Dam Name: {details.get('dam_name', 'N/A')}")
        output.append('')
        output.append('BREEDER INFORMATION:')
        output.append('-' * 30)
        output.append(f"Breeder ID: {details.get('breeder_id', 'N/A')}")
        output.append(f"Breeder Name: {details.get('breeder_name', 'N/A')}")
        output.append('')
        output.append('DATES AND STATUS:')
        output.append('-' * 30)
        output.append(f"Date of Birth: {details.get('dob', 'N/A')}")
        output.append(f"Disposal Date: {details.get('disposal', 'N/A')}")
        output.append(f"Service Type: {details.get('service_type', 'N/A')}")
        output.append(f"Status: {details.get('status', 'N/A')}")
        output.append('')
        output.append('=' * 80)
        return '\n'.join(output) 