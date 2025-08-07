#!/usr/bin/env python3
"""
Main Entry Point for Digital Beef Scraper
Modular menu system for different scraper types
"""

import asyncio
import sys
from typing import Optional
from playwright.async_api import async_playwright, Browser, Page
from ranch_scraper.cli import RanchScraperCLI
from epd_scraper.cli import EPDSearchCLI


class DigitalBeefScraper:
    """Main application with menu system for different scrapers"""
    
    def __init__(self):
        self.base_url = "https://shorthorn.digitalbeef.com"
        self.browser = None
        self.playwright = None
        self.page = None
    
    async def init_browser(self) -> bool:
        """Initialize Playwright browser"""
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=True)
            self.page = await self.browser.new_page()
            return True
        except Exception as e:
            print(f"Error initializing browser: {e}")
            return False
    
    async def navigate_to_site(self) -> bool:
        """Navigate to the Digital Beef website"""
        try:
            print(f"Navigating to {self.base_url}")
            await self.page.goto(self.base_url, wait_until='networkidle')
            print("Successfully loaded Digital Beef website")
            return True
        except Exception as e:
            print(f"Error navigating to site: {e}")
            return False
    
    def show_menu(self):
        """Display the main menu"""
        print("\n" + "=" * 50)
        print("Welcome to Digital Beef Scraper")
        print("What would you like to do?")
        print("1. Ranch Search")
        print("2. EPD Search")
        print("3. Animal Search (coming soon)")
        print("4. Exit")
        print("=" * 50)
    
    def get_user_choice(self) -> Optional[int]:
        """Get user menu choice"""
        try:
            choice = input("Select an option [1-4]: ").strip()
            return int(choice)
        except ValueError:
            print("Invalid input. Please enter a number between 1 and 4.")
            return None
        except KeyboardInterrupt:
            print("\nExiting...")
            return 4
    
    async def run_ranch_search(self):
        """Run the ranch search functionality"""
        print("\n=== Ranch Search ===")
        try:
            cli = RanchScraperCLI()
            await cli.main_with_page(self.page)
        except Exception as e:
            print(f"Error in ranch search: {e}")
    
    async def run_epd_search(self):
        """Run the EPD search functionality"""
        print("\n=== EPD Search ===")
        try:
            cli = EPDSearchCLI()
            await cli.main_with_page(self.page)
        except Exception as e:
            print(f"Error in EPD search: {e}")
    
    async def run_animal_search(self):
        """Run animal search (placeholder)"""
        print("\n=== Animal Search ===")
        print("Animal Search coming soon...")
        print("This feature will be implemented in a future update.")
        input("Press Enter to continue...")
    
    async def cleanup(self):
        """Clean up browser resources"""
        try:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            print(f"Warning: Error during cleanup: {e}")
    
    async def main_loop(self):
        """Main application loop"""
        while True:
            try:
                self.show_menu()
                choice = self.get_user_choice()
                
                if choice is None:
                    continue
                
                if choice == 1:
                    await self.run_ranch_search()
                elif choice == 2:
                    await self.run_epd_search()
                elif choice == 3:
                    await self.run_animal_search()
                elif choice == 4:
                    print("Exiting Digital Beef Scraper...")
                    break
                else:
                    print("Invalid choice. Please select 1-4.")
                    
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"Unexpected error: {e}")
                print("Returning to main menu...")
    
    async def run(self):
        """Main application entry point"""
        try:
            # Initialize browser
            if not await self.init_browser():
                print("Failed to initialize browser. Exiting.")
                return
            
            # Navigate to site
            if not await self.navigate_to_site():
                print("Failed to navigate to website. Exiting.")
                return
            
            # Run main loop
            await self.main_loop()
            
        except Exception as e:
            print(f"Critical error: {e}")
        finally:
            # Always cleanup
            await self.cleanup()


async def main():
    """Main entry point"""
    app = DigitalBeefScraper()
    await app.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1) 