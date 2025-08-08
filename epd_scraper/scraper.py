import asyncio
from typing import List, Dict, Any, Optional, Tuple
from playwright.async_api import async_playwright, Browser, Page
from .form_parser import EPDFormParser
from ranch_scraper.utils import clean_table_data, format_table_output

class EPDSearchScraper:

    def __init__(self, base_url: str='https://shorthorn.digitalbeef.com'):
        self.base_url = base_url
        self.form_parser = EPDFormParser()
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

    async def wait_for_epd_form_ready(self, page: Page) -> bool:
        try:
            await page.wait_for_selector('#epd_search', timeout=10000)
            print('EPD Search form loaded successfully')
            return True
        except Exception as e:
            print(f'Error waiting for EPD form: {e}')
            return False

    async def validate_form_structure(self, page: Page) -> Tuple[bool, List[str]]:
        return await self.form_parser.validate_required_fields(page)

    async def fill_search_form(self, page: Page, search_params: Dict[str, str]) -> bool:
        try:
            print('Filling EPD search form...')
            success = await self.form_parser.fill_epd_form(page, search_params)
            if success:
                print('EPD search form filled successfully')
            else:
                print('Failed to fill EPD search form')
            return success
        except Exception as e:
            print(f'Error filling EPD search form: {e}')
            return False

    async def trigger_search(self, page: Page) -> bool:
        try:
            print('Triggering EPD search...')
            await page.evaluate('doSearch_Epd();')
            print('EPD search triggered successfully')
            return True
        except Exception as e:
            print(f'Error triggering EPD search: {e}')
            return False

    async def wait_for_results(self, page: Page) -> bool:
        try:
            print('Waiting for EPD search results...')
            max_wait_time = 120
            check_interval = 2
            elapsed_time = 0
            while elapsed_time < max_wait_time:
                has_results = await page.evaluate('\n                    () => {\n                        const resultRows = document.querySelectorAll(\'tr[id^="tr_"]\');\n                        return resultRows.length > 0;\n                    }\n                ')
                if has_results:
                    print(f'EPD search results loaded successfully after {elapsed_time} seconds')
                    return True
                no_results = await page.evaluate("\n                    () => {\n                        const noResultsMsg = document.querySelector('.no-results, .no-data, .error');\n                        const loadingMsg = document.querySelector('.loading, .processing');\n                        return {\n                            noResults: noResultsMsg !== null,\n                            loading: loadingMsg !== null\n                        };\n                    }\n                ")
                if no_results['noResults']:
                    print('No EPD results found')
                    return True
                if not no_results['loading']:
                    await page.wait_for_timeout(1000)
                    elapsed_time += 1
                    continue
                await page.wait_for_timeout(check_interval * 1000)
                elapsed_time += check_interval
                if elapsed_time % 10 == 0:
                    print(f'Still waiting for results... ({elapsed_time}s elapsed)')
            print(f'Search timeout after {max_wait_time} seconds')
            return True
        except Exception as e:
            print(f'Error waiting for EPD results: {e}')
            return False

    async def extract_table_data(self, page: Page) -> List[Dict[str, str]]:
        try:
            epd_data = await page.evaluate('\n                () => {\n                    const results = [];\n                    const rows = document.querySelectorAll(\'tr[id^="tr_"]\');\n                    \n                    for (const row of rows) {\n                        const animalData = {};\n                        \n                        // Extract animal registration and name from first cell\n                        const firstCell = row.querySelector(\'td:first-child\');\n                        if (firstCell) {\n                            const regLink = firstCell.querySelector(\'a\');\n                            if (regLink) {\n                                animalData[\'registration\'] = regLink.textContent.trim();\n                                animalData[\'registration_url\'] = regLink.href;\n                            }\n                            \n                            // Extract tattoo and name from nested table\n                            const nestedTable = firstCell.querySelector(\'table\');\n                            if (nestedTable) {\n                                const tattooRow = nestedTable.querySelector(\'tr:nth-child(2) td\');\n                                if (tattooRow) {\n                                    animalData[\'tattoo\'] = tattooRow.textContent.trim();\n                                }\n                                \n                                const nameRow = nestedTable.querySelector(\'tr:nth-child(3) td\');\n                                if (nameRow) {\n                                    animalData[\'name\'] = nameRow.textContent.trim();\n                                }\n                            }\n                        }\n                        \n                        // Extract EPD values from cells with border-left:thin style\n                        const epdCells = row.querySelectorAll(\'td[style*="border-left:thin"]\');\n                        const traits = [\'CED\', \'BW\', \'WW\', \'YW\', \'MK\', \'TM\', \'CEM\', \'ST\', \'YG\', \'CW\', \'REA\', \'FAT\', \'MB\', \'$CEZ\', \'$BMI\', \'$CPI\', \'$F\'];\n                        \n                        for (let i = 0; i < epdCells.length && i < traits.length; i++) {\n                            const cell = epdCells[i];\n                            const trait = traits[i];\n                            \n                            const nestedTable = cell.querySelector(\'table\');\n                            if (nestedTable) {\n                                const rows = nestedTable.querySelectorAll(\'tr\');\n                                \n                                if (rows.length >= 4) {\n                                    // EPD value (first row)\n                                    const epdValue = rows[0]?.querySelector(\'td\')?.textContent.trim() || \'\';\n                                    animalData[`${trait}_epd`] = epdValue;\n                                    \n                                    // Change value (second row)\n                                    const changeValue = rows[1]?.querySelector(\'td\')?.textContent.trim() || \'\';\n                                    animalData[`${trait}_change`] = changeValue;\n                                    \n                                    // Accuracy (third row)\n                                    const accuracy = rows[2]?.querySelector(\'td\')?.textContent.trim() || \'\';\n                                    animalData[`${trait}_acc`] = accuracy;\n                                    \n                                    // Rank (fourth row)\n                                    const rank = rows[3]?.querySelector(\'td\')?.textContent.trim() || \'\';\n                                    animalData[`${trait}_rank`] = rank;\n                                }\n                            }\n                        }\n                        \n                        if (Object.keys(animalData).length > 0) {\n                            results.push(animalData);\n                        }\n                    }\n                    \n                    return results;\n                }\n            ')
            cleaned_data = clean_table_data(epd_data)
            print(f'Found {len(cleaned_data)} EPD entries')
            return cleaned_data
        except Exception as e:
            print(f'Error extracting EPD table data: {e}')
            return []

    async def scrape_epd(self, search_params: Dict[str, str]) -> List[Dict[str, str]]:
        try:
            self.browser, self.playwright = await self.init_browser()
            page = await self.browser.new_page()
            if not await self.navigate_to_site(page):
                return []
            if not await self.wait_for_epd_form_ready(page):
                return []
            is_valid, missing_fields = await self.validate_form_structure(page)
            if not is_valid:
                print(f'Missing required EPD fields: {missing_fields}')
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
            print(f'Error during EPD scraping: {e}')
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

    def format_results(self, results: List[Dict[str, str]]) -> str:
        if not results:
            return 'No EPD results found.'
        output = []
        output.append('=' * 80)
        output.append('EPD SEARCH RESULTS')
        output.append('=' * 80)
        output.append(f'Total Animals Found: {len(results)}')
        output.append('')
        for i, animal in enumerate(results, 1):
            output.append(f'Animal #{i}')
            output.append('-' * 40)
            output.append(f"Registration: {animal.get('registration', 'N/A')}")
            output.append(f"Tattoo: {animal.get('tattoo', 'N/A')}")
            output.append(f"Name: {animal.get('name', 'N/A')}")
            output.append('')
            output.append('Growth & Maternal EPDs:')
            growth_traits = ['CED', 'BW', 'WW', 'YW', 'MK', 'TM', 'CEM', 'ST']
            for trait in growth_traits:
                epd = animal.get(f'{trait}_epd', 'N/A')
                change = animal.get(f'{trait}_change', 'N/A')
                acc = animal.get(f'{trait}_acc', 'N/A')
                rank = animal.get(f'{trait}_rank', 'N/A')
                output.append(f'  {trait:>3}: EPD={epd:>6} | Change={change:>6} | Acc={acc:>5} | Rank={rank:>4}')
            output.append('')
            output.append('Carcass EPDs:')
            carcass_traits = ['YG', 'CW', 'REA', 'FAT', 'MB']
            for trait in carcass_traits:
                epd = animal.get(f'{trait}_epd', 'N/A')
                change = animal.get(f'{trait}_change', 'N/A')
                acc = animal.get(f'{trait}_acc', 'N/A')
                rank = animal.get(f'{trait}_rank', 'N/A')
                output.append(f'  {trait:>3}: EPD={epd:>6} | Change={change:>6} | Acc={acc:>5} | Rank={rank:>4}')
            output.append('')
            output.append('Index EPDs:')
            index_traits = ['CEZ', 'BMI', 'CPI', 'F']
            for trait in index_traits:
                epd = animal.get(f'{trait}_epd', 'N/A')
                change = animal.get(f'{trait}_change', 'N/A')
                acc = animal.get(f'{trait}_acc', 'N/A')
                rank = animal.get(f'{trait}_rank', 'N/A')
                output.append(f'  {trait:>3}: EPD={epd:>6} | Change={change:>6} | Acc={acc:>5} | Rank={rank:>4}')
            output.append('')
            output.append('=' * 80)
            output.append('')
        return '\n'.join(output)

    def format_results_table(self, results: List[Dict[str, str]]) -> str:
        if not results:
            return 'No EPD results found.'
        return format_table_output(results)

    async def extract_animal_detail(self, page: Page, animal_url: str) -> Dict[str, str]:
        try:
            print(f'Extracting animal details from: {animal_url}')
            await page.goto(animal_url, wait_until='networkidle')
            await page.wait_for_selector('table[style*="min-width:850px"]', timeout=10000)
            details = await page.evaluate("\n                () => {\n                    const details = {};\n                    \n                    // Extract basic identification info\n                    const rows = document.querySelectorAll('tr');\n                    for (const row of rows) {\n                        const cells = row.querySelectorAll('td');\n                        if (cells.length >= 2) {\n                            const label = cells[0]?.textContent?.trim();\n                            const value = cells[1]?.textContent?.trim();\n                            \n                            if (label && value) {\n                                if (label.includes('Sex:')) details.sex = value;\n                                if (label.includes('Name:')) details.name = value;\n                                if (label.includes('Registration:')) details.registration = value;\n                                if (label.includes('International ID:')) details.international_id = value;\n                                if (label.includes('EID:')) details.eid = value;\n                                if (label.includes('Horn/Poll/Scur:')) details.horn_poll_scur = value;\n                                if (label.includes('Shorthorn %:')) details.shorthorn_percent = value;\n                                if (label.includes('COI:')) details.coi = value;\n                                if (label.includes('Service Type:')) details.service_type = value;\n                                if (label.includes('Status:')) details.status = value;\n                                if (label.includes('Color:')) details.color = value;\n                                if (label.includes('DOB:')) details.dob = value;\n                                if (label.includes('Disposal:')) details.disposal = value;\n                            }\n                        }\n                    }\n                    \n                    // Extract Sire and Dam info\n                    const sireRow = Array.from(rows).find(row => \n                        row.textContent.includes('Sire:') || row.textContent.includes('Sire:&nbsp;')\n                    );\n                    if (sireRow) {\n                        const sireLink = sireRow.querySelector('a');\n                        if (sireLink) {\n                            details.sire_registration = sireLink.textContent.trim();\n                            details.sire_name = sireRow.textContent.split('&nbsp;').pop()?.trim() || '';\n                        }\n                    }\n                    \n                    const damRow = Array.from(rows).find(row => \n                        row.textContent.includes('Dam:') || row.textContent.includes('Dam:&nbsp;')\n                    );\n                    if (damRow) {\n                        const damLink = damRow.querySelector('a');\n                        if (damLink) {\n                            details.dam_registration = damLink.textContent.trim();\n                            details.dam_name = damRow.textContent.split('&nbsp;').pop()?.trim() || '';\n                        }\n                    }\n                    \n                    // Extract Breeder info\n                    const breederRow = Array.from(rows).find(row => \n                        row.textContent.includes('Breeder:') || row.textContent.includes('Breeder:&nbsp;')\n                    );\n                    if (breederRow) {\n                        const breederLink = breederRow.querySelector('a');\n                        if (breederLink) {\n                            details.breeder_id = breederLink.textContent.trim();\n                            details.breeder_name = breederRow.textContent.split('(').pop()?.split(')')[0]?.trim() || '';\n                        }\n                    }\n                    \n                    // Extract Herd Prefix and Tattoo info\n                    const herdPrefixRow = Array.from(rows).find(row => \n                        row.textContent.includes('Herd Prefix:') || row.textContent.includes('Tattoo')\n                    );\n                    if (herdPrefixRow) {\n                        const text = herdPrefixRow.textContent;\n                        const prefixMatch = text.match(/Herd Prefix:.*?Tattoo.*?:\\s*([A-Z]+)\\s*:\\s*([A-Z0-9]+)/);\n                        if (prefixMatch) {\n                            details.herd_prefix = prefixMatch[1];\n                            details.tattoo = prefixMatch[2];\n                        }\n                    }\n                    \n                    return details;\n                }\n            ")
            print(f"Extracted animal details for {details.get('registration', 'Unknown')}")
            return details
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
