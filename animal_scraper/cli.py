import asyncio
from typing import Dict, Optional
from playwright.async_api import Page
from .scraper import AnimalSearchScraper
from ranch_scraper.exporter import DynamicExporter

class AnimalSearchCLI:

    def __init__(self):
        self.scraper = AnimalSearchScraper()
        self.exporter = DynamicExporter()

    def _prompt_sex(self) -> str:
        print('\n--- Search For ---')
        print('1. Bulls (B)')
        print('2. Females (C)')
        print('3. Both (default)')
        choice = input('Enter choice (1-3, press Enter for Both): ').strip()
        if choice == '1':
            return 'B'
        if choice == '2':
            return 'C'
        return ''

    def _prompt_field(self) -> str:
        print('\n--- Search Field ---')
        fields = [('Reg #', 'animal_registration'), ('Tattoo', 'animal_private_herd_id'), ('Name', 'animal_name'), ('EID', 'eid')]
        for i, (label, value) in enumerate(fields, 1):
            print(f'{i}. {label}')
        raw = input("Choose field (1-4), press Enter for 'Reg #': ").strip()
        if not raw:
            return 'animal_registration'
        try:
            idx = int(raw)
            if 1 <= idx <= len(fields):
                return fields[idx - 1][1]
        except ValueError:
            pass
        # allow direct value entry
        if raw in [v for _, v in fields]:
            return raw
        print('Invalid choice. Using default Reg #.')
        return 'animal_registration'

    def _prompt_value(self) -> str:
        print('\n--- Search Value ---')
        print('Use an asterisk (*) as a wildcard')
        return input('Value: ').strip()

    async def main_with_page(self, page: Page):
        try:
            if not await self.scraper.wait_for_form_ready(page):
                print('Failed to load Animal search form')
                return
            sex = self._prompt_sex()
            field = self._prompt_field()
            value = self._prompt_value()
            params: Dict[str, str] = {'sex': sex, 'field': field, 'value': value}
            results = await self.scraper.scrape_animals(params)
            if not results:
                print('No animal results found')
                return
            print('\n' + self.scraper.format_results(results))
            await self._show_follow_up_menu(results)
        except Exception as e:
            print(f'Error in Animal scraper: {e}')

    async def _show_follow_up_menu(self, data):
        while True:
            print('\nWhat would you like to do next?')
            print('1. Export results to CSV')
            print('2. Export results to JSON')
            print('3. View animal details')
            print('4. Return to main menu')
            try:
                choice = input('\nEnter your choice (1-4): ').strip()
                if choice == '1':
                    filename = input("Enter CSV filename (or press Enter for 'animal_results.csv'): ").strip()
                    if not filename:
                        filename = 'animal_results.csv'
                    exported_file = self.exporter.export_to_csv(data, filename)
                    if exported_file:
                        print(f'Results exported to: {exported_file}')
                    break
                elif choice == '2':
                    filename = input("Enter JSON filename (or press Enter for 'animal_results.json'): ").strip()
                    if not filename:
                        filename = 'animal_results.json'
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

    async def _view_animal_details(self, data):
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
        registration = animal.get('registration')
        registration_url = animal.get('registration_url')
        if not registration_url:
            print('No detail URL available for this animal.')
            return
        print(f"\nFetching details for {registration}...")
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

    async def _view_all_animal_details(self, data):
        print(f'\nFetching details for all {len(data)} animals...')
        enriched_results = []
        for i, animal in enumerate(data, 1):
            print(f"\nProcessing animal {i}/{len(data)}: {animal.get('registration', 'Unknown')}")
            registration = animal.get('registration')
            registration_url = animal.get('registration_url')
            if not registration_url:
                print('  Skipping: No detail URL available')
                enriched_results.append(animal)
                continue
            try:
                self.scraper.browser, self.scraper.playwright = await self.scraper.init_browser()
                page = await self.scraper.browser.new_page()
                details = await self.scraper.extract_animal_detail(page, registration_url)
                enriched = animal.copy()
                enriched.update(details)
                enriched_results.append(enriched)
            except Exception as e:
                print(f'  Error: {e}')
                enriched_results.append(animal)
        print('\n' + self.scraper.format_results(enriched_results))

async def main():
    cli = AnimalSearchCLI()
    await cli.main()
if __name__ == '__main__':
    asyncio.run(main()) 