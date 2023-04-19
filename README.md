# 2022-2023 ADU Machine Learning Course Dataset Collection
## Yusuf Metin Özer - yusuf.ozer@adu.edu.tr
____
## Description
This project is a simple keylogger that logs the pressed keys and mouse movements. Then saves them to a file. The keylogger is written in Python and uses the `pynput` library. The keylogger is based on the [1] project. The keylogger is written for Windows operating system. The keylogger is written in Python 3.11.2 and tested on Windows 11.
## Installation
``` ps1
cd ml_project
python -m venv .
.\Scripts\Activate.ps1  # Windows (PowerShell)
.\Scripts\activate.bat  # Windows (Command Prompt)
source Scripts/activate # Linux
pip install -r requirements.txt
```
## Usage
``` ps1
python activity_track.py
```
Or you can use the `output/activity_track.exe` file to run the program.

### Note
* Key combination listings not working properly. for example, `ctrl + alt`. 
___
## References
- [1] https://github.com/secureyourself7/python-keylogger