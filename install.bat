@echo off
echo Installing Ranch Scraper Dependencies...
echo ======================================

echo.
echo Installing Python packages...
pip install -r requirements.txt

echo.
echo Installing Playwright browsers...
playwright install

echo.
echo Testing installation...
python main.py --list-locations

echo.
echo Installation complete!
echo.
echo Usage examples:
echo   python ranch_scraper.py --help
echo   python ranch_scraper.py --name "Red*"
echo   python ranch_scraper.py --city "Dallas" --export csv
echo.
pause 