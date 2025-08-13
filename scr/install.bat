@echo off
setlocal
echo Install Script v2, dsc.gg/arizaltd
REM Check if the directory already exists
if exist "selflyphotos" (
  echo The 'selflyphotos' directory already exists. Skipping git clone.
  cd selflyphotos\selfly
) else (
  REM Clone the repository
  echo Cloning the repository...
  git clone https://github.com/jamielocal/selflyphotos
  cd selflyphotos\selfly
)

REM Create a virtual environment
echo Creating virtual environment...
echo NOTE: Depending on your PC, it might take a bit for this step to Complete, just give it time and it will
python -m venv venv

REM Activate the virtual environment and install dependencies
echo Activating virtual environment and installing dependencies...
call venv\Scripts\activate.bat
pip install Flask requests Pillow

REM Run the application
echo Starting the application...
python app.py

endlocal
