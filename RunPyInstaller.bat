@REM Create a single executable on this OS (Windows)
@REM

REM For testing purposes:
REM SET DEST_DIR="C:\MIkesStuff\Pers\Dropbox\Work\Courses\NewGradingTool"

SET DEST_DIR="C:\MIkesStuff\Pers\Dropbox\Personal\home\PersonalTool"
SET VENV=venv3_10

echo Generating PersonalTool and copying it into %DEST_DIR%

@call %VENV%\Scripts\activate.bat

echo ######################## Make the PersonalTool program ####################################

set PYTHONOPTIMIZE=1 && %VENV%\Scripts\pyinstaller.exe Main.py --onedir --clean --noconfirm

echo .
echo .
echo .
echo .
echo .
echo .
echo Replace existing GradingTool with this new one:

echo    Remove existing dir:
rmdir /s /q %DEST_DIR%

echo    Make replacement dir:
mkdir %DEST_DIR%

echo    Move working stuff into final dir:
ren dist\Main\Main.exe pt.exe
robocopy dist/Main %DEST_DIR% /MIR
REM cp -t %DEST_DIR% -r dist/Main/*
REM xcopy dist/Main %DEST_DIR% /c /e REM xcopy truncates long file names which messes up most of the .dlls
REM move dist/Main %DEST_DIR%
REM copy /Y dist\gt.exe %DEST_DIR%


timeout /t 30

echo .
echo .
echo .

echo remove the PyInstaller temp dirs
rmdir /S /Q build
rmdir /S /Q dist

call %VENV%\Scripts\deactivate.bat
