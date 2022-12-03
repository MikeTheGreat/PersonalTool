@REM Create a single executable on this OS (Windows, Mac, Linux)
@REM

SET DEST_DIR="C:\MIkesStuff\Pers\Dropbox\Personal\home\PersonalTool"
echo "Generating PersonalTool and copying it into " $DEST_DIR

@call venv_3-9_min\Scripts\activate.bat

echo ######################## Make the PersonalTool program ####################################

set PYTHONOPTIMIZE=1 && venv_3-9_min\Scripts\pyinstaller.exe Main.py --onedir --clean --noconfirm

echo .
echo .
echo .
echo .
echo .
echo .
echo Replace existing PersonalTool with this new one:

echo    Remove existing dir
rmdir /s /q $DEST_DIR

echo    Make replacement dir
mkdir $DEST_DIR

echo Rename Main.exe to be pt.exe
ren dist\Main\Main.exe pt.exe

echo    Move working stuff into final dir
REM move dist/Main $DEST_DIR
cp -t $DEST_DIR -r dist/Main/*

REM copy /Y dist\gt.exe $DEST_DIR


timeout /t 30

echo .
echo .
echo .

echo remove the PyInstaller temp dirs
REM rmdir /S /Q build
REM rmdir /S /Q dist

call venv_3-9_min\Scripts\deactivate.bat
