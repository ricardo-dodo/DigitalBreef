import argparse
import asyncio
import sys
from typing import Dict, List, Optional
from playwright.async_api import Page
from .scraper import DynamicScraper
from .exporter import DynamicExporter
from .utils import validate_search_params, parse_location_input, sanitize_filename

class RanchScraperCLI:

    def __init__(self):
        self.scraper = DynamicScraper()
        self.exporter = DynamicExporter()

    def parse_arguments(self) -> argparse.Namespace:
        parser = argparse.ArgumentParser(description='Dynamic Ranch Scraper for Digital Beef Shorthorn', formatter_class=argparse.RawDescriptionHelpFormatter, epilog='\nExamples:\n  python main.py --name "Red*" --city "Dallas" --location "Texas"\n  python main.py --prefix "ZZZ" --export csv\n  python main.py --location "TX" --output results.csv\n  python main.py --list-locations\n  python main.py (runs in interactive mode)\n        ')
        parser.add_argument('--name', help='Ranch name filter')
        parser.add_argument('--city', help='City filter')
        parser.add_argument('--prefix', help='Herd prefix filter')
        parser.add_argument('--member_id', help='Member ID filter')
        parser.add_argument('--location', help='Location filter (supports multiple formats)')
        parser.add_argument('--export', choices=['csv', 'json'], help='Export format')
        parser.add_argument('--output', help='Output filename')
        parser.add_argument('--list-locations', action='store_true', help='List available locations')
        parser.add_argument('--form-info', action='store_true', help='Show form structure information')
        return parser.parse_args()

    def get_search_params_from_args(self, args: argparse.Namespace) -> Dict[str, str]:
        params = {}
        if args.name:
            params['name'] = args.name.strip()
        if args.city:
            params['city'] = args.city.strip()
        if args.prefix:
            params['prefix'] = args.prefix.strip()
        if args.member_id:
            params['member_id'] = args.member_id.strip()
        if args.location:
            params['location'] = args.location.strip()
        return params

    async def get_available_locations(self) -> List[Dict[str, str]]:
        try:
            browser, playwright = await self.scraper.init_browser()
            page = await browser.new_page()
            await self.scraper.navigate_to_site(page)
            await self.scraper.wait_for_form_ready(page)
            locations = await self.scraper.get_available_locations(page)
            await browser.close()
            await playwright.stop()
            return locations
        except Exception as e:
            print(f'Error getting locations: {e}')
            return []

    async def list_locations(self):
        print('Fetching available locations...')
        locations = await self.get_available_locations()
        if not locations:
            print('No locations found or error occurred')
            return
        print(f'\nAvailable locations ({len(locations)} total):')
        print('=' * 60)
        for i, location in enumerate(locations, 1):
            print(f"{i:3d}. {location['text']:<40} ({location['value']})")
        print('=' * 60)
        print('Usage examples:')
        print("  --location 'Texas'")
        print("  --location 'TX'")
        print("  --location 'United States|TX'")

    async def show_form_info(self):
        print('Fetching form information...')
        try:
            browser, playwright = await self.scraper.init_browser()
            page = await browser.new_page()
            form_info = await self.scraper.get_form_info(page)
            await browser.close()
            await playwright.stop()
            if form_info:
                print('\nForm Structure Information:')
                print('=' * 40)
                if 'form_structure' in form_info:
                    fields = form_info['form_structure'].get('fields', {})
                    print(f'Available fields ({len(fields)}):')
                    for field_id, field_info in fields.items():
                        print(f"  - {field_id}: {field_info.get('type', 'unknown')}")
                if 'search_button' in form_info:
                    button_info = form_info['search_button']
                    print(f'\nSearch button:')
                    print(f"  - Has function: {button_info.get('hasFunction', False)}")
                    if button_info.get('button'):
                        print(f"  - Button: {button_info['button'].get('value', 'N/A')}")
                if 'available_locations' in form_info:
                    locations = form_info['available_locations']
                    print(f'\nAvailable locations: {len(locations)}')
                    for i, location in enumerate(locations[:5], 1):
                        print(f"  {i}. {location['text']}")
                    if len(locations) > 5:
                        print(f'  ... and {len(locations) - 5} more')
            else:
                print('Could not retrieve form information')
        except Exception as e:
            print(f'Error getting form info: {e}')

    async def run_scraper(self, search_params: Dict[str, str], export_format: Optional[str]=None, output_filename: Optional[str]=None):
        print(f'\nSearching with parameters: {search_params}')
        results = await self.scraper.scrape_ranches(search_params)
        if not results:
            print('No results found')
            return
        print('\n' + self.scraper.format_results(results))
        if export_format:
            if output_filename:
                exported_file = self.exporter.export_data(results, export_format, output_filename)
            else:
                exported_file = self.exporter.export_data(results, export_format)
            if exported_file:
                print(f'Results exported to: {exported_file}')

    async def main(self):
        args = self.parse_arguments()
        if args.list_locations:
            await self.list_locations()
            return
        if args.form_info:
            await self.show_form_info()
            return
        search_params = self.get_search_params_from_args(args)
        is_valid, errors = validate_search_params(search_params)
        if not is_valid:
            print('Validation errors:')
            for error in errors:
                print(f'  - {error}')
            print('\nUse --help for usage information')
            print('Run without arguments for interactive mode')
            sys.exit(1)
        await self.run_scraper(search_params, args.export, args.output)

    async def main_with_page(self, page: Page):
        try:
            if not await self.scraper.wait_for_form_ready(page):
                print('Failed to load search form')
                return
            from .interactive_prompt import InteractivePrompt
            interactive_prompt = InteractivePrompt()
            params, export_format, filename = await interactive_prompt.run_interactive_mode(page)
            if not params:
                print('No search parameters provided. Exiting.')
                return
            results = await self.scraper.scrape_ranches(params)
            if not results:
                print('No results found')
                return
            print('\n' + self.scraper.format_results(results))
            await self._show_follow_up_menu(results, page)
        except Exception as e:
            print(f'Error in ranch scraper: {e}')

    async def _show_follow_up_menu(self, data: List[Dict[str, str]], page: Page):
        while True:
            print('\nWhat would you like to do next?')
            print('1. Export results to CSV')
            print('2. Export results to JSON')
            print("3. View a member's full detail")
            print('4. New search')
            print('5. Return to main menu')
            try:
                choice = input('\nEnter your choice (1-5): ').strip()
                if choice == '1':
                    filename = input("Enter CSV filename (or press Enter for 'ranch_results.csv'): ").strip()
                    if not filename:
                        filename = 'ranch_results.csv'
                    exported_file = self.exporter.export_to_csv(data, filename)
                    if exported_file:
                        print(f'Results exported to: {exported_file}')
                elif choice == '2':
                    filename = input("Enter JSON filename (or press Enter for 'ranch_results.json'): ").strip()
                    if not filename:
                        filename = 'ranch_results.json'
                    exported_file = self.exporter.export_to_json(data, filename)
                    if exported_file:
                        print(f'Results exported to: {exported_file}')
                elif choice == '3':
                    updated = await self._view_member_detail(data, page)
                    if isinstance(updated, list) and updated:
                        data = updated
                        print('\n' + self.scraper.format_results(data))
                elif choice == '4':
                    from .interactive_prompt import InteractivePrompt
                    interactive_prompt = InteractivePrompt()
                    params, _, _ = await interactive_prompt.run_interactive_mode(page)
                    if not params:
                        print('No search parameters provided.')
                        continue
                    new_results = await self.scraper.scrape_ranches(params)
                    if not new_results:
                        print('No results found')
                        continue
                    data = new_results
                    print('\n' + self.scraper.format_results(data))
                elif choice == '5':
                    print('Returning to main menu...')
                    break
                else:
                    print('Invalid choice. Please enter 1, 2, 3, 4, or 5.')
            except KeyboardInterrupt:
                print('\nOperation cancelled.')
                break
            except Exception as e:
                print(f'Error: {e}')
                # Keep the loop running

    async def _view_member_detail(self, data: List[Dict[str, str]], page: Page) -> List[Dict[str, str]]:
        if not data:
            print('No data available to view details.')
            return data
        print(f'\nAvailable members ({len(data)} total):')
        for i, member in enumerate(data, 1):
            member_id = member.get('member_id', member.get('Member ID', 'Unknown'))
            member_name = member.get('member_name', member.get('Member Name', 'Unknown'))
            print(f'{i}. {member_id} - {member_name}')
        print(f'\nView options:')
        print('1. View one member detail')
        print('2. View all members detail')
        print('3. Cancel')
        while True:
            try:
                choice = input(f'\nEnter your choice (1-3): ').strip()
                if choice == '1':
                    return await self._view_single_member_detail(data, page)
                elif choice == '2':
                    return await self._view_all_members_detail(data, page)
                elif choice == '3':
                    print('Cancelled.')
                    return data
                else:
                    print('Invalid choice. Please enter 1, 2, or 3.')
            except KeyboardInterrupt:
                print('\nOperation cancelled.')
                return data
            except Exception as e:
                print(f'Error: {e}')
                return data

    async def _show_member_detail(self, member, page) -> Optional[Dict[str, str]]:
        print(f'\n=== Member Detail ===')
        print(f"Member ID: {member.get('member_id', 'N/A')}")
        print(f"Member Name: {member.get('member_name', 'N/A')}")
        print(f"Herd Prefix: {member.get('herd_prefix', 'N/A')}")
        print(f"DBA: {member.get('dba', 'N/A')}")
        print(f"City: {member.get('city', 'N/A')}")
        print(f"State: {member.get('state', 'N/A')}")
        member_id_html = member.get('member_id_html', member.get('member_id', ''))
        if not member_id_html:
            print('No member ID found for detail view.')
            return None
        if '<a href=' in member_id_html:
            import re
            url_match = re.search('href="([^"]+)"', member_id_html)
            if url_match:
                profile_url = url_match.group(1).replace('&amp;', '&')
                print(f'\nFetching detailed profile information...')
                try:
                    await page.goto(profile_url, wait_until='networkidle', timeout=15000)
                    from .utils import parse_profile_table
                    profile_details = await parse_profile_table(page)
                    # Also enrich with addresses/phones/contacts
                    member_id_match = re.search('member_id=(\d+)', profile_url)
                    addresses = []
                    phones = []
                    contacts = []
                    if member_id_match:
                        member_id_num = member_id_match.group(1)
                        addresses = await self._get_addresses(page, member_id_num)
                        phones = await self._get_phones(page, member_id_num)
                        contacts = await self._get_contacts(page, member_id_num)
                    enriched_member = member.copy()
                    enriched_member.update(profile_details)
                    enriched_member['addresses'] = addresses
                    enriched_member['phones'] = phones
                    enriched_member['contacts'] = contacts
                    if 'member_id_html' in enriched_member:
                        del enriched_member['member_id_html']
                    return enriched_member
                except Exception as e:
                    print(f'Error fetching profile details: {e}')
                    return None
            else:
                print('Could not extract profile URL.')
                return None
        else:
            print('No profile link found for this member.')
            return None

    async def _get_addresses(self, page, member_id):
        try:
            await page.click('#tab-bg\\:2')
            await page.wait_for_selector('#ajax_ranch_canvass table', timeout=10000)
            addresses = await page.evaluate("\n                () => {\n                    const table = document.querySelector('#ajax_ranch_canvass table');\n                    if (!table) return [];\n                    \n                    const rows = table.querySelectorAll('tr');\n                    const addresses = [];\n                    \n                    for (let i = 1; i < rows.length; i++) { // Skip header row\n                        const cells = rows[i].querySelectorAll('td');\n                        if (cells.length >= 8) {\n                            const address = {\n                                type: cells[0].textContent.trim(),\n                                street: cells[1].textContent.trim(),\n                                city: cells[2].textContent.trim(),\n                                state: cells[3].textContent.trim(),\n                                postal_code: cells[4].textContent.trim(),\n                                country: cells[5].textContent.trim(),\n                                premise_id: cells[6].textContent.trim(),\n                                email: cells[7].textContent.trim()\n                            };\n                            addresses.push(address);\n                        }\n                    }\n                    \n                    return addresses;\n                }\n            ")
            return addresses
        except Exception as e:
            print(f'Error getting addresses: {e}')
            return []

    async def _get_phones(self, page, member_id):
        try:
            await page.click('#tab-bg\\:3')
            await page.wait_for_selector('#ajax_ranch_canvass table', timeout=10000)
            phones = await page.evaluate("\n                () => {\n                    const table = document.querySelector('#ajax_ranch_canvass table');\n                    if (!table) return [];\n                    \n                    const rows = table.querySelectorAll('tr');\n                    const phones = [];\n                    \n                    for (let i = 1; i < rows.length; i++) { // Skip header row\n                        const cells = rows[i].querySelectorAll('td');\n                        if (cells.length >= 6) {\n                            const countryCode = cells[1].textContent.trim();\n                            const areaCode = cells[2].textContent.trim();\n                            const prefix = cells[3].textContent.trim();\n                            const suffix = cells[4].textContent.trim();\n                            const extension = cells[5].textContent.trim();\n                            \n                            const phone = {\n                                type: cells[0].textContent.trim(),\n                                country_code: countryCode,\n                                area_code: areaCode,\n                                prefix: prefix,\n                                suffix: suffix,\n                                extension: extension,\n                                full_number: `${countryCode}${areaCode}${prefix}${suffix}${extension}`.replace(/\\s+/g, '')\n                            };\n                            phones.push(phone);\n                        }\n                    }\n                    \n                    return phones;\n                }\n            ")
            return phones
        except Exception as e:
            print(f'Error getting phones: {e}')
            return []

    async def _get_contacts(self, page, member_id):
        try:
            await page.click('#tab-bg\\:1')
            await page.wait_for_selector('#ajax_ranch_canvass table', timeout=10000)
            contacts = await page.evaluate("\n                () => {\n                    const table = document.querySelector('#ajax_ranch_canvass table');\n                    if (!table) return [];\n                    \n                    const rows = table.querySelectorAll('tr');\n                    const contacts = [];\n                    \n                    for (let i = 1; i < rows.length; i++) { // Skip header row\n                        const cells = rows[i].querySelectorAll('td');\n                        if (cells.length >= 7) {\n                            const contact = {\n                                job_title: cells[1].textContent.trim(),\n                                name: cells[2].textContent.trim(),\n                                nickname: cells[3].textContent.trim(),\n                                email: cells[4].textContent.trim(),\n                                phone: cells[5].textContent.trim(),\n                                address: cells[6].textContent.trim()\n                            };\n                            contacts.push(contact);\n                        }\n                    }\n                    \n                    return contacts;\n                }\n            ")
            return contacts
        except Exception as e:
            print(f'Error getting contacts: {e}')
            return []

    async def _view_single_member_detail(self, data: List[Dict[str, str]], page: Page) -> List[Dict[str, str]]:
        while True:
            try:
                choice = input(f"\nEnter member number (1-{len(data)}) or 'q' to quit: ").strip()
                if choice.lower() == 'q':
                    print('Cancelled.')
                    return data
                try:
                    member_index = int(choice) - 1
                    if 0 <= member_index < len(data):
                        selected_member = data[member_index]
                        enriched = await self._show_member_detail(selected_member, page)
                        if enriched:
                            new_data = data.copy()
                            new_data[member_index] = enriched
                            return new_data
                        return data
                    else:
                        print(f'Invalid choice. Please enter a number between 1 and {len(data)}.')
                except ValueError:
                    print("Invalid input. Please enter a number or 'q' to quit.")
            except KeyboardInterrupt:
                print('\nOperation cancelled.')
                return data
            except Exception as e:
                print(f'Error: {e}')
                return data

    async def _view_all_members_detail(self, data, page) -> List[Dict[str, str]]:
        print(f'\nFetching details for all {len(data)} members...')
        enriched_results = []
        for i, member in enumerate(data, 1):
            print(f"\nProcessing member {i}/{len(data)}: {member.get('member_id', 'Unknown')}")
            member_id_html = member.get('member_id_html', member.get('member_id', ''))
            if not member_id_html:
                print(f'  Skipping: No member ID found')
                enriched_results.append(member)
                continue
            if '<a href=' in member_id_html:
                import re
                url_match = re.search('href="([^"]+)"', member_id_html)
                if url_match:
                    profile_url = url_match.group(1).replace('&amp;', '&')
                    try:
                        await page.goto(profile_url, wait_until='networkidle', timeout=15000)
                        from .utils import parse_profile_table
                        profile_details = await parse_profile_table(page)
                        import re
                        member_id_match = re.search('member_id=(\\d+)', profile_url)
                        if member_id_match:
                            member_id_num = member_id_match.group(1)
                            addresses = await self._get_addresses(page, member_id_num)
                            phones = await self._get_phones(page, member_id_num)
                            contacts = await self._get_contacts(page, member_id_num)
                            profile_details['addresses'] = addresses
                            profile_details['phones'] = phones
                            profile_details['contacts'] = contacts
                        enriched_member = member.copy()
                        enriched_member.update(profile_details)
                        if 'member_id_html' in enriched_member:
                            del enriched_member['member_id_html']
                        enriched_results.append(enriched_member)
                        print(f"  ✓ Enriched: {profile_details.get('breeder_type', 'N/A')} - {profile_details.get('profile_type', 'N/A')}")
                        if profile_details.get('addresses'):
                            print(f'    Addresses: {len(profile_details.get('addresses', []))} found')
                        if profile_details.get('phones'):
                            print(f'    Phones: {len(profile_details.get('phones', []))} found')
                        if profile_details.get('contacts'):
                            print(f'    Contacts: {len(profile_details.get('contacts', []))} found')
                    except Exception as e:
                        print(f'  ✗ Error: {e}')
                        enriched_member = member.copy()
                        enriched_member.update({'breeder_type': '', 'profile_type': '', 'profile_id': '', 'profile_name': '', 'dba': '', 'herd_prefix': '', 'addresses': [], 'phones': [], 'contacts': []})
                        enriched_results.append(enriched_member)
                else:
                    print(f'  Skipping: Could not extract profile URL')
                    enriched_results.append(member)
            else:
                print(f'  Skipping: No profile link found')
                enriched_results.append(member)
        print(f'\nEnrichment complete. {len(enriched_results)} results processed.')
        print('\n' + self.scraper.format_results(enriched_results))
        return enriched_results

async def main():
    cli = RanchScraperCLI()
    await cli.main()
if __name__ == '__main__':
    asyncio.run(main())
