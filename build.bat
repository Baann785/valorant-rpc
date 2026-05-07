@echo off
setlocal

pushd "%~dp0"

echo Installing requirements...
python -m pip install -r requirements.txt --upgrade
if errorlevel 1 goto failed

echo Building with PyInstaller...
python -m PyInstaller valorant-rpc.spec --clean --noconfirm
if errorlevel 1 goto failed

echo Build complete! Check the 'dist' folder.
popd
pause
exit /B 0

:failed
echo Build failed.
popd
pause
exit /B 1
