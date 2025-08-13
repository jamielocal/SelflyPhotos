@echo off
setlocal

REM Check if the directory already exists
if exist "selflyphotos" (
  echo The 'selflyphotos' directory already exists. Skipping git clone.
  cd selflyphotos
) else (
  REM Clone the repository
  echo Cloning the repository...
  git clone https://github.com/jamielocal/selflyphotos
  cd selflyphotos
)

REM Create a virtual environment
echo Creating virtual environment...
python -m venv venv

REM Activate the virtual environment and install dependencies
echo Activating virtual environment and installing dependencies...
call venv\Scripts\activate.bat
pip install Flask requests Pillow

REM Run the application
echo Starting the application...
python app.py

endlocal