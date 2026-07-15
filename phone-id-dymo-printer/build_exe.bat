@echo off
REM Builds a standalone Windows .exe so the app can run without a Python install.
setlocal

python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller

python -m PyInstaller --onefile --noconsole --name "PhoneID-DymoPrinter" app.py

echo.
echo Build finished. Find the executable at dist\PhoneID-DymoPrinter.exe
echo Copy config.example.json next to the .exe as config.json if you want custom settings.
endlocal
