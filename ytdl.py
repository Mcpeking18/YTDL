import os
import shutil
from yt_dlp import YoutubeDL as YTDL

url = str(input("Copy & Paste Your Url : "))

temp_path = r'C:/Rishi/Temp' # saving to ssd ok ? cuz FAST AS FUCKBOII
output_path = r'D:/Rishi/hehe downloading stuff from yt' #SAVING TO MAI FUCKING HDD 
os.makedirs(temp_path, exist_ok=True)

ydl_opts = {
    'outtmpl': os.path.join(temp_path, '%(title)s.%(ext)s'), 
    'format': 'bv*+ba/best',  
    'postprocessors': [{
        'key': 'FFmpegVideoConvertor',  
        'preferedformat': 'mp4',  
    }],
    'merge_output_format': 'mp4'
}

with YTDL(ydl_opts) as ydl:
    info = ydl.extract_info(url)
    filename = ydl.prepare_filename(info).replace(info['ext'], 'mp4')


if os.path.exists(filename):
    shutil.move(filename, output_path)
    print(f"File moved to: {output_path}")
else:
    print("Error: File not found!")