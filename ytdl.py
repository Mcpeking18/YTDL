import os
import shutil
from yt_dlp import YoutubeDL as YTDL

url = str(input("Copy & Paste Your Url : "))

temp_path = r'C:/Rishi/Temp' # saving to ssd ok ? cuz FAST AS FUCKBOII
output_path = r'D:/Desktop' #SAVING TO MAI FUCKING HDD 
os.makedirs(temp_path, exist_ok=True)

user = input("what mp3 or mp4")

quality_and_type = {
    'audio_only' : ['mp3','ba/best'],
    'video' : ['mp4','bv*+ba/best']
}

def func_ydl_opts(x):
    ydl_opts = {
        'outtmpl': os.path.join(temp_path, '%(title)s.%(ext)s'),
        'format': x[1],
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',  
            'preferedformat': x[0],  
        }],
        # 'merge_output_format': user
    }
    return ydl_opts

if user == "mp3":
    ydl_opts = func_ydl_opts(quality_and_type['audio_only'])
else:
    ydl_opts = func_ydl_opts(quality_and_type['video'])

# if user == "mp3":
#     ydl_opts = {
#         'format': 'ba/best',
#         'outtmpl': os.path.join(temp_path, '%(title)s.%(ext)s'),
#         'postprocessors': [{
#             'key': 'FFmpegVideoConvertor',  
#             'preferedformat': 'mp3',  
#         }]
#     }
# else:
#     ydl_opts = {
#         'outtmpl': os.path.join(temp_path, '%(title)s.%(ext)s'), 
#         'format': 'bv*+ba/best',  
#         'postprocessors': [{
#             'key': 'FFmpegVideoConvertor',  
#             'preferedformat': 'mp4',  
#         }],
#         'merge_output_format': 'mp4'
#     }

with YTDL(ydl_opts) as ydl:
    info = ydl.extract_info(url)
    # info['title'] += user
    # print(info['title'])
    filename = ydl.prepare_filename(info).replace(info['ext'], user)


if os.path.exists(filename):
    shutil.move(filename, output_path)
    print(f"File moved to: {output_path}")
else:
    print("Error: File not found!")