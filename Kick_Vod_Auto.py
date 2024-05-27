import os
import json
import time
import random
from datetime import datetime
import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options
import subprocess
import re

# these paths and filenames need to be created. the script does not create them for you. File types must be json
chrome_driver_path = r"D:\Downloads\chromedriver-win64 (3)\chromedriver-win64\chromedriver.exe"
chrome_binary_path = r"D:\Downloads\chrome-win64 (1)\chrome-win64\chrome.exe"
json_data_path = r'\Automation_files\json\prev_video_pull_v1.json'
json_links_path = r'\Automation_files\json\prev_video_links_v1.json'
json_vod_path = r'\Automation_files\json\prev_video_vod_v1.json'
json_download_path = r'\Automation_files\json\prev_video_download_v1.json'
target_directory = "Your target dir"

# Setup Chrome options
chrome_options = Options()
chrome_options.binary_location = chrome_binary_path
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--disable-extensions')
chrome_options.add_argument('--disable-popup-blocking')
chrome_options.add_argument('--disable-infobars')
chrome_options.add_argument(r"user-data-dir=C:\Users\Administrator\AppData\Local\Google\Chrome\User Data")

def log_error(message):
    print(message)
    with open('error_log.txt', 'a') as log_file:
        log_file.write(f"{datetime.now()} - {message}\n")

def countdown(seconds):
    for i in range(seconds, 0, -1):
        print(f"Waiting... {i} seconds remaining", end='\r')
        time.sleep(1)
    print()

def fetch_json_data(url):
    driver = uc.Chrome(options=chrome_options, driver_executable_path=chrome_driver_path)
    try:
        print(f"Fetching URL: {url}")
        driver.get(url)
        countdown(10)  # Countdown for the 10 seconds wait
        page_source = driver.page_source
        json_start = page_source.find('{')
        json_end = page_source.rfind('}') + 1
        if json_start == -1 or json_end == -1:
            raise ValueError("Failed to find JSON data in the page source")
        json_data = page_source[json_start:json_end]
        return json.loads(json_data)
    except Exception as e:
        log_error(f'Error fetching data from {url}: {e}')
        return None
    finally:
        driver.quit()

def find_video_uuids(data):
    uuids = []
    if isinstance(data, dict):
        if 'video' in data and 'uuid' in data['video']:
            uuids.append(data['video']['uuid'])
        for value in data.values():
            uuids.extend(find_video_uuids(value))
    elif isinstance(data, list):
        for item in data:
            uuids.extend(find_video_uuids(item))
    return uuids

def extract_vod_details(url):
    driver = uc.Chrome(options=chrome_options, driver_executable_path=chrome_driver_path)
    try:
        print(f"Fetching URL: {url}")
        driver.get(url)
        countdown(10)
        page_source = driver.page_source
        json_start = page_source.find('{')
        json_end = page_source.rfind('}') + 1
        json_data = page_source[json_start:json_end]
        data = json.loads(json_data)
        source = data.get('source')
        created_at = data.get('created_at')
        session_title = data['livestream'].get('session_title') if data.get('livestream') else None
        return source, created_at, session_title
    except Exception as e:
        log_error(f'Error fetching data from {url}: {e}')
        return None, None, None
    finally:
        driver.quit()

def is_valid_m3u8_url(url):
    return url.lower().endswith(".m3u8")

def extract_date_from_url(url):
    match = re.search(r"/(\d{4})/(\d{1,2})/(\d{1,2})/", url)
    if match:
        year, month, day = match.groups()
        month = str(int(month)).zfill(2)
        day = str(int(day)).zfill(2)
        return year, month, day
    return None, None, None

def generate_output_text(base_title, date_string, existing_titles):
    base_title_with_date = f"{base_title} - {date_string}"
    if base_title_with_date not in existing_titles:
        existing_titles[base_title_with_date] = 1
        return f"{base_title_with_date} part1", 1
    else:
        part = existing_titles[base_title_with_date] + 1
        existing_titles[base_title_with_date] = part
        return f"{base_title_with_date} part{part}", part

def main():
    # Step 1: Fetch JSON data from URL and save to file, you must change the channel name to the channel you are looking to download from, example: https://kick.com/api/v1/channels/CHANNEL NAME
    url = 'CHANGE ME!!!'
    data = fetch_json_data(url)
    if data:
        with open(json_data_path, 'w') as json_file:
            json.dump(data, json_file)
        print(f"Data successfully saved to {json_data_path}")

    # Step 2: Extract video UUIDs and save video links to file
    if os.path.exists(json_data_path):
        with open(json_data_path, 'r') as file:
            data = json.load(file)
            uuids = find_video_uuids(data)
            video_links = [{"video_json_link": f"https://kick.com/api/v1/video/{uuid}", "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')} for uuid in uuids]
            with open(json_links_path, 'w') as outfile:
                json.dump(video_links, outfile, indent=4)
            print(f"Video links saved to {json_links_path}")

    # Step 3: Fetch VOD details and save to file
    if os.path.exists(json_links_path):
        with open(json_links_path, 'r') as infile:
            video_links = json.load(infile)
            results = []
            for entry in video_links:
                url = entry.get('video_json_link')
                if url:
                    source, created_at, session_title = extract_vod_details(url)
                    if source and created_at and session_title:
                        results.append({
                            "video_json_link": url,
                            "source": source,
                            "created_at": created_at,
                            "session_title": session_title
                        })
            with open(json_vod_path, 'w') as outfile:
                json.dump(results, outfile, indent=4)
            print(f"VOD details saved to {json_vod_path}")

    # Step 4: Download videos and save download details to file
    if os.path.exists(json_vod_path):
        with open(json_vod_path, 'r') as json_file:
            data = json.load(json_file)
        if os.path.exists(json_download_path):
            with open(json_download_path, 'r') as outfile:
                try:
                    output_data = json.load(outfile)
                except json.JSONDecodeError:
                    output_data = []
        else:
            output_data = []
        existing_entries = {entry['source']: entry for entry in output_data}
        existing_titles = {entry['video_title']: int(re.search(r'part(\d+)', entry['episode']).group(1)) if 'episode' in entry and re.search(r'part(\d+)', entry['episode']) else 1 for entry in output_data}

        download_count = 0
        skip_count = 0

        for entry in data:
            m3u8_url = entry.get('source')
            if m3u8_url and is_valid_m3u8_url(m3u8_url):
                if m3u8_url in existing_entries and 'download_end' in existing_entries[m3u8_url]:
                    print(f"Skipping URL: {m3u8_url} (already downloaded)")
                    skip_count += 1
                    continue

                year, month, day = extract_date_from_url(m3u8_url)
                # change your base_title to what ever you want!!!
                base_title = "CHANGE ME!!"
                date_string = f"{month}-{day}-{year}" if year and month and day else "Unknown Date"
                video_title, part = generate_output_text(base_title, date_string, existing_titles)

                print(f"Downloading video from URL: {m3u8_url}")
                output_file = os.path.join(target_directory, f"{video_title}.%(ext)s")
                entry['video_title'] = video_title
                entry['episode'] = f"part{part}"
                entry['download_start'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                yt_dlp_command = [
                    # path to your yt-dlp change as needed!
                    "d:\\Downloads\\YouTube Downloader\\August\\yt-dlp_win\\yt-dlp",
                    "-P", target_directory,
                    "-o", output_file,
                    m3u8_url
                ]
                subprocess.run(yt_dlp_command)
                entry['download_end'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                existing_entries[m3u8_url] = entry
                download_count += 1
            else:
                print("Invalid m3u8 URL or m3u8 URL not found in entry.")
        
        with open(json_download_path, 'w') as json_file:
            json.dump(list(existing_entries.values()), json_file, indent=4)

        print(f"Total number of downloads: {download_count}")
        print(f"Total number of skips: {skip_count}")

if __name__ == "__main__":
    main()
