@echo off
echo Installing requirements...
pip install -r requirements.txt

echo Building executable...
pyinstaller --onefile --paths=D:\TestCaseManagements --name TestCaseManagement --icon=icons/app.ico --noconsole ^
--add-data "controllers;controllers" ^
--add-data "config;config" ^
main.py
#pyinstaller --onefile --paths=D:\TestCaseManagements main.py

echo Build complete! Executable is in the dist folder.
pause
