import os
import shutil
from yt_dlp import YoutubeDL as YTDL

temp_path = r'C:/Temp'   # Temporary fast download folder
output_path = r'D:/Desktop'  # Final output folder

os.makedirs(temp_path, exist_ok=True) #checking folders
os.makedirs(output_path, exist_ok=True) #checking folders

def progress(d):
    if d['status'] == 'finished':
        ext = d.get('info_dict', {}).get('ext')
        if ext in ['mp3', 'mp4']:
            print("\nDownload finished, now post-processing...")

def main():
    while True:
        url = input("\nCopy & Paste Your URL (or 'q' to quit): ").strip() #Supported Url's ofc
        if url.lower() == 'q':
            break
        if not url:
            continue

        print("\nWhat do you want to download?\n"
        "1 - Audio (mp3)\n"
        "2 - Video (mp4)\n")
        user = input("Enter choice (1/2): ").strip()

        if user == "1":
            ydl_opts = {
                'outtmpl': os.path.join(temp_path, '%(title)s.%(ext)s'),
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192'
                }],
                'progress_hooks': [progress]
            }
        elif user == "2":
            ydl_opts = {
                'outtmpl': os.path.join(temp_path, '%(title)s %(resolution)s.%(ext)s'),
                'format': 'bestvideo[vcodec^=avc1]+bestaudio[acodec^=mp4a]/mp4',
                #IDK MIGHT USE THIS LATER
                # 'postprocessors': [{
                #     'key': 'FFmpegVideoConvertor',  
                #     'preferedformat': 'mp4',  
                # }],
                'merge_output_format': 'mp4',
                'progress_hooks': [progress]
            }
        else:
            print("Invalid choice. Please try again.")
            continue

        try:
            with YTDL(ydl_opts) as ydl:
                print("\nStarting download...")
                ydl.download([url])

            for file in os.listdir(temp_path):
                source = os.path.join(temp_path, file)
                destination = os.path.join(output_path, file)
                if os.path.isfile(source):
                    shutil.move(source, destination)
                    print(f"✅ Moved: {file} -> {output_path}")

            print("\nDone :D")

        except KeyboardInterrupt:
            print("\n❌ Download cancelled by user.")
        except Exception as e:
            print(f"\n❌ Error: {e}")
            with open("errors.txt", "a") as file:
                file.write(f" Error: {e}\n")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nGoodbye!")


#add failsafes
#option to restart 
#learn gui
#idk more bs