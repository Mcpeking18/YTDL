import os
import shutil
from yt_dlp import YoutubeDL as YTDL

url = str(input("Copy & Paste Your Url : "))

temp_path = r'C:/Temp' # saving to ssd ok ? cuz FAST AS FUCKBOII
# output_path = r'D:/Desktop' #SAVING TO MAI FUCKING HDD 
os.makedirs(temp_path, exist_ok=True)

output_path = os.path# os.makedirs(output_path, exist_ok=True)


user = int(input("What do you want to download\n"
"Just the audio or video\n"
"Enter 1 for Audio and 2 for Video"))

if user == 1:
    ydl_opts = {
        'outtmpl': os.path.join(temp_path, '%(title)s.%(ext)s'),
        'format': 'ba/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',  
            'preferredcodec': 'mp3',
            'preferredquality': '192'
        }]
    }

else:
    ydl_opts = {
        'outtmpl': os.path.join(temp_path, '%(title)s.%(ext)s'), 
        'format': 'bv*+ba/best',  
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',  
            'preferedformat': 'mp4',  
        }],
        'merge_output_format': 'mp4'
    }

try:
    with YTDL(ydl_opts) as ydl:
        print("Downloading...")
        info = ydl.extract_info(url)
        # ydl.download([url])
        filename = ydl.prepare_filename(info).replace(info['ext'], user)
        print("Download complete.")

except Exception as e:
    print(f"An error occurred: {e}")

if os.path.exists(filename):
    shutil.move(filename, output_path)
    print(f"File moved to: {output_path}")
    os.rmdir(temp_path)
else:
    print("Error: File not found!")