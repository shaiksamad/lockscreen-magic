import os
import subprocess

import json
from random import choice
import datetime
import logging
import sys

logging.basicConfig(filename="changes.log", level="DEBUG", format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S')

try:
    import requests
except ModuleNotFoundError:
    try:
        subprocess.run("pip install requests", shell=True, check=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        import requests
    except subprocess.CalledProcessError as e:
        logging.error(f"Can't install/import requests module. error: {e}")


# check previous update time
try:
    with open("LASTRUN") as f:
        today = datetime.datetime.today()
        if today.date() == datetime.datetime.strptime(f.read(), "%Y-%m-%d %H:%M:%S").date():
            logging.info("Already Updated Today. Next update on tomorrow.")
            sys.exit("Already Updated Today. Next update on tomorrow.")
except FileNotFoundError:
    pass

# loading config file
with open('./config.dev.json') as f:
    config = json.loads(f.read())


# validating config file
if 'api_token' not in config or type(config['api_token']) is not str or not config['api_token']:
    logging.info(f"Invalid api_token `{config['api_token']}`.  Get your API Key from https://pexels.com/api")
    sys.exit(1)

if 'query' not in config or config["query"] == "":
    logging.info("Invalid query. query example: \"nature wallpaper\"")
    sys.exit(1)

if "orientation" in config and config["orientation"] not in ["", "landscape", "portrait"]:
    logging.info("Invalid orientation. orientation can be portrait ot landscape")
    # sys.exit(1)

if "size" in config and config["size"] not in ["", "small", "medium", "large"]:
    logging.info("Invalid size. size can be small, medium, large")
    # sys.exit(1)

if 'page' in config and type(config['page']) is not int:
    logging.info("Invalid page. page should be integer.")
    # sys.exit(1)

if "per_page" in config and type(config["per_page"]) is not int:
    logging.info("Invalid per_page. per_page should be integer.")
    # sys.exit(1)

if "src_size" not in config and config['src_type'] not in ['original', 'large', 'large2x', 'small', 'medium', 'portrait', 'landscape', 'tiny']:
    logging.info("Invalid 'src_size'. src_size should be 'original', 'large', 'large2x', 'small', 'medium', 'portrait', 'landscape', 'tiny'")
    sys.exit(1)

if 'min_width' in config and type(config["min_width"]) is not int:
    logging.info("Invalid min_width. `min_width` should be int.")
    # sys.exit(1)


# path to store fetched image
temp_path = os.path.join(os.getcwd(), "temp")


base_url = "https://api.pexels.com/v1"

headers = {
    "Authorization": config['api_token']
}

params = {
    "query": config["query"],
    "orientation": config["orientation"],
    "per_page": config["per_page"],
    "size": config["size"],
    "color": config["color"]    
}

photos = []


def fetch_photos(url=f"{base_url}/search", params=params):
    """
    get the list of photos,
    skip photos which are completed,
    add unique photos to photos list.
    """

    try:
        # searching for list of photos
        resp = requests.api.get(url, params=params, headers=headers)
        resp.raise_for_status()
    except Exception as e:
        logging.error(f"can't search photos. error: {e}")
        sys.exit(e)

    data = resp.json()

    try:
        with open("COMPLETED") as f:
            completed = f.read()
    except FileNotFoundError:
        completed = ""


    for photo in data['photos']:

        if photo['src']['original'] in completed:
            continue

        if config['must_have_alt'] and ('alt' not in photo):
            continue
        
        if photo["width"] > config["min_width"]:
            photos.append(photo['src']['original'])
    
    # if all the photos are in COMPLETED list then goto next page
    if not photos:
        fetch_photos(data['next_page'])


# populates the photo array with new photos
fetch_photos()

selected = choice(photos)


try:
    # fetching selected image data
    resp = requests.api.get(selected)
    resp.raise_for_status()
except Exception as e:
    logging.error(f"Failed to download image:  {e}")
    sys.exit(e)


# saving fetched image
if 'x-imgix-id' in resp.headers:
    temp_file = resp.headers['x-imgix-id'] + os.path.splitext(selected)[-1]
    temp_file = os.path.join(temp_path, temp_file)
else:
    temp_file = os.path.join(temp_path, os.path.basename(selected))

with open(temp_file, 'wb') as f:
    f.write(resp.content)

logging.info(f"Image Saved at: {temp_file}")


# setting image as lockscreen
try:
    subprocess.run(f"igcmdWin10.exe setlockimage {os.path.abspath(temp_file)}",
                   shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    logging.info("Lockscreen image updated")
except subprocess.CalledProcessError as e:
    logging.error(f"Cant set lockscreen image. error: {e}")


# adding the image url to COMPLETED list.
with open("COMPLETED", 'a') as f:
    f.write(selected + "\n")

logging.info(f"Image added to COMPLETED list: {selected}")


# setting current datetime to LASTRUN
with open("LASTRUN", 'w') as f:
    lastrun = datetime.datetime.today().strftime("%Y-%m-%d %H:%M:%S")
    f.write(lastrun)


logging.info(f"LASTRUN: {lastrun}")


def cleanup_wallpapers():
    wallpapers = os.listdir(temp_path)

    current_date = datetime.datetime.today()

    for wp in wallpapers:
        wp_path = os.path.join(temp_path, wp)
        wp_created = datetime.datetime.fromtimestamp(os.path.getctime(wp_path))

        if (current_date - wp_created).days > config['image_cleanup_after']:
            os.remove(wp_path)
        

# cleanig old images
cleanup_wallpapers()

logging.info(f"cleaned up old wallpapers.")

