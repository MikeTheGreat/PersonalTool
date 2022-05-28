@REM Create a single executable on this OS (Windows, Mac, Linux)
@REM

@call venv_3-9_min\Scripts\activate.bat

echo ######################## Make the PersonalTool program ####################################

REM set PYTHONOPTIMIZE=1 && venv_3-9_min\Scripts\pyinstaller.exe Main.py --onedir --clean --noconfirm

echo .
echo .
echo .
echo .
echo .
echo .
echo Replace existing PersonalTool with this new one:

echo    Remove existing dir
rmdir /s /q C:\MikesStuff\Pers\Dropbox\Work\bin\PersonalTool

echo    Make replacement dir
mkdir C:\MikesStuff\Pers\Dropbox\Work\bin\PersonalTool

echo Rename Main.exe to be pt.exe
ren dist\Main\Main.exe pt.exe

echo    Move working stuff into final dir
REM move dist/Main C:\MikesStuff\Pers\Dropbox\Work\bin\PersonalTool
cp -t C:\MikesStuff\Pers\Dropbox\Work\bin\PersonalTool -r dist/Main/*

REM copy /Y dist\gt.exe C:\MikesStuff\Pers\Dropbox\Work\bin


timeout /t 30

echo .
echo .
echo .

echo remove the PyInstaller temp dirs
REM rmdir /S /Q build
REM rmdir /S /Q dist

call venv_3-9_min\Scripts\deactivate.bat
