# BatchCompressor
ffmpeg/bin/ le exe et ces dll

# Usage
pyinstaller --onefile --windowed --add-data "ffmpeg/bin/ffmpeg.exe;ffmpeg/bin" --clean main.py
