import asyncio
from typing import Dict, List, Optional
from playwright.async_api import Page
from .scraper import EPDSearchScraper
from ranch_scraper.exporter import DynamicExporter

class EPDSearchCLI:

    def __init__(self):
        self.scraper = EPDSearchScraper()
        self.exporter = DynamicExporter()

    async def collect_epd_parameters(self, page: Page) -> Dict[str, str]:
        print('=== EPD Search Interactive Mode ===')
        print('Enter EPD search parameters (press Enter to skip):')
        print()
        params = {}
        traits = self.scraper.form_parser.get_epd_traits()
        print('Available EPD traits:')
        for i, trait in enumerate(traits, 1):
            print(f'{i}. {trait}')
        print()
        for trait in traits:
            trait_key = trait.lower().replace(' ', '_').replace('$', '')
            print(f'\n--- {trait} ---')
            min_val = input(f'Minimum {trait} (or press Enter to skip): ').strip()
            if min_val:
                params[f'{trait_key}_min'] = min_val
            max_val = input(f'Maximum {trait} (or press Enter to skip): ').strip()
            if max_val:
                params[f'{trait_key}_max'] = max_val
            trait_fields = self.scraper.form_parser.get_trait_fields(trait)
            if trait_fields.get('acc'):
                acc_val = input(f'Minimum accuracy for {trait} (or press Enter to skip): ').strip()
                if acc_val:
                    params[f'{trait_key}_acc'] = acc_val
        print('\n--- Sort Options ---')
        print('Available sort fields:')
        for trait in traits:
            trait_fields = self.scraper.form_parser.get_trait_fields(trait)
            sort_value = trait_fields.get('sort')
            if sort_value:
                print(f'- {trait}: {sort_value}')
        sort_choice = input("\nEnter sort field (or press Enter for default 'epd_ww'): ").strip()
        if sort_choice:
            params['sort_field'] = sort_choice
        else:
            params['sort_field'] = 'epd_ww'
        print('\n--- Sex Filter ---')
        print('1. Bulls (B)')
        print('2. Females (C)')
        print('3. Both (default)')
        sex_choice = input('Enter choice (1-3, or press Enter for Both): ').strip()
        if sex_choice == '1':
            params['search_sex'] = 'B'
        elif sex_choice == '2':
            params['search_sex'] = 'C'
        else:
            params['search_sex'] = ''
        return params

    async def main_with_page(self, page: Page):
        try:
            if not await self.scraper.wait_for_epd_form_ready(page):
                print('Failed to load EPD search form')
                return
            params = await self.collect_epd_parameters(page)
            if not params:
                print('No search parameters provided. Exiting.')
                return
            results = await self.scraper.scrape_epd(params)
            if not results:
                print('No EPD results found')
                return
            print('\nHow would you like to display the results?')
            print('1. Detailed format (organized by categories)')
            print('2. Table format (simple table)')
            format_choice = input('\nEnter your choice (1-2, default 1): ').strip()
            if format_choice == '2':
                formatted_results = self.scraper.format_results_table(results)
            else:
                formatted_results = self.scraper.format_results(results)
            print('\n' + formatted_results)
            await self._show_follow_up_menu(results)
        except Exception as e:
            print(f'Error in EPD scraper: {e}')

    async def _show_follow_up_menu(self, data):
        while True:
            print('\nWhat would you like to do next?')
            print('1. Export results to CSV')
            print('2. Export results to JSON')
            print('3. View animal details')
            print('4. Return to main menu')
            try:
                choice = input('\nEnter your choice (1-3): ').strip()
                if choice == '1':
                    filename = input("Enter CSV filename (or press Enter for 'epd_results.csv'): ").strip()
                    if not filename:
                        filename = 'epd_results.csv'
                    exported_file = self.exporter.export_to_csv(data, filename)
                    if exported_file:
                        print(f'Results exported to: {exported_file}')
                    break
                elif choice == '2':
                    filename = input("Enter JSON filename (or press Enter for 'epd_results.json'): ").strip()
                    if not filename:
                        filename = 'epd_results.json'
                    exported_file = self.exporter.export_to_json(data, filename)
                    if exported_file:
                        print(f'Results exported to: {exported_file}')
                    break
                elif choice == '3':
                    await self._view_animal_details(data)
                    break
                elif choice == '4':
                    print('Returning to main menu...')
                    break
                else:
                    print('Invalid choice. Please enter 1, 2, 3, or 4.')
            except KeyboardInterrupt:
                print('\nOperation cancelled.')
                break
            except Exception as e:
                print(f'Error: {e}')
                break

    async def _view_animal_details(self, data: List[Dict[str, str]]):
        if not data:
            print('No data available for viewing details.')
            return
        print(f'\nFound {len(data)} animals. Which one would you like to view details for?')
        for i, animal in enumerate(data, 1):
            registration = animal.get('registration', 'Unknown')
            name = animal.get('name', 'Unknown')
            print(f'{i}. {registration} - {name}')
        print(f'{len(data) + 1}. View all animals details')
        print(f'{len(data) + 2}. Cancel')
        try:
            choice = input(f'\nEnter your choice (1-{len(data) + 2}): ').strip()
            if choice.isdigit():
                choice_num = int(choice)
                if choice_num == len(data) + 1:
                    await self._view_all_animal_details(data)
                elif choice_num == len(data) + 2:
                    print('Cancelled.')
                    return
                elif 1 <= choice_num <= len(data):
                    selected_animal = data[choice_num - 1]
                    await self._view_single_animal_detail(selected_animal)
                else:
                    print('Invalid choice.')
            else:
                print('Invalid input. Please enter a number.')
        except KeyboardInterrupt:
            print('\nOperation cancelled.')
        except Exception as e:
            print(f'Error: {e}')

    async def _view_single_animal_detail(self, animal: Dict[str, str]):
        registration_url = animal.get('registration_url')
        if not registration_url:
            print('No detail URL available for this animal.')
            return
        print(f"\nFetching details for {animal.get('registration', 'Unknown')}...")
        try:
            self.scraper.browser, self.scraper.playwright = await self.scraper.init_browser()
            page = await self.scraper.browser.new_page()
            details = await self.scraper.extract_animal_detail(page, registration_url)
            if details:
                formatted_details = self.scraper.format_animal_detail(details)
                print('\n' + formatted_details)
            else:
                print('Failed to extract animal details.')
        except Exception as e:
            print(f'Error viewing animal details: {e}')
        finally:
            if self.scraper.browser:
                try:
                    await self.scraper.browser.close()
                except Exception as e:
                    print(f'Warning: Error closing browser: {e}')
            if self.scraper.playwright:
                try:
                    await self.scraper.playwright.stop()
                except Exception as e:
                    print(f'Warning: Error stopping playwright: {e}')

    async def _view_all_animal_details(self, data: List[Dict[str, str]]):
        print(f'\nFetching details for all {len(data)} animals...')
        try:
            self.scraper.browser, self.scraper.playwright = await self.scraper.init_browser()
            page = await self.scraper.browser.new_page()
            all_details = []
            for i, animal in enumerate(data, 1):
                registration_url = animal.get('registration_url')
                if not registration_url:
                    print(f"Skipping {animal.get('registration', 'Unknown')} - no URL available")
                    continue
                print(f"Processing {i}/{len(data)}: {animal.get('registration', 'Unknown')}")
                try:
                    details = await self.scraper.extract_animal_detail(page, registration_url)
                    if details:
                        merged_data = {**animal, **details}
                        all_details.append(merged_data)
                    else:
                        print(f"Failed to extract details for {animal.get('registration', 'Unknown')}")
                except Exception as e:
                    print(f"Error processing {animal.get('registration', 'Unknown')}: {e}")
                    continue
            if all_details:
                print(f'\nSuccessfully extracted details for {len(all_details)} animals.')
                print('\nHow would you like to display the detailed results?')
                print('1. Detailed format (organized by categories)')
                print('2. Table format (simple table)')
                format_choice = input('\nEnter your choice (1-2, default 1): ').strip()
                if format_choice == '2':
                    formatted_results = self.scraper.format_results_table(all_details)
                else:
                    formatted_results = self.scraper.format_results(all_details)
                print('\n' + formatted_results)
                await self._show_export_menu(all_details)
            else:
                print('No animal details were successfully extracted.')
        except Exception as e:
            print(f'Error viewing all animal details: {e}')
        finally:
            if self.scraper.browser:
                try:
                    await self.scraper.browser.close()
                except Exception as e:
                    print(f'Warning: Error closing browser: {e}')
            if self.scraper.playwright:
                try:
                    await self.scraper.playwright.stop()
                except Exception as e:
                    print(f'Warning: Error stopping playwright: {e}')

    async def _show_export_menu(self, data: List[Dict[str, str]]):
        while True:
            print('\nWould you like to export the detailed results?')
            print('1. Export to CSV')
            print('2. Export to JSON')
            print('3. Skip export')
            try:
                choice = input('\nEnter your choice (1-3): ').strip()
                if choice == '1':
                    filename = input("Enter CSV filename (or press Enter for 'epd_detailed_results.csv'): ").strip()
                    if not filename:
                        filename = 'epd_detailed_results.csv'
                    exported_file = self.exporter.export_to_csv(data, filename)
                    if exported_file:
                        print(f'Detailed results exported to: {exported_file}')
                    break
                elif choice == '2':
                    filename = input("Enter JSON filename (or press Enter for 'epd_detailed_results.json'): ").strip()
                    if not filename:
                        filename = 'epd_detailed_results.json'
                    exported_file = self.exporter.export_to_json(data, filename)
                    if exported_file:
                        print(f'Detailed results exported to: {exported_file}')
                    break
                elif choice == '3':
                    print('Skipping export.')
                    break
                else:
                    print('Invalid choice. Please enter 1, 2, or 3.')
            except KeyboardInterrupt:
                print('\nOperation cancelled.')
                break
            except Exception as e:
                print(f'Error: {e}')
                break

async def main():
    cli = EPDSearchCLI()
    await cli.main()
if __name__ == '__main__':
    asyncio.run(main())
