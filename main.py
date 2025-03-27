"""This script downloads images from URLs listed in an Excel file.

It handles concurrent downloads, logs errors, and saves the images in a specified output directory.

It uses asyncio for concurrent downloads and httpx for making HTTP requests."""

import os
import json
import random
from datetime import datetime
import asyncio
from urllib.parse import urlparse
import httpx
import pandas as pd
from tqdm import tqdm
import sys


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 OPR/109.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
]

def main():
    """ Main function to read the configuration, initialize the error log, and start the download process."""
    print("Starting program...")
    with open("config.json", "r") as config_file:
        config = json.load(config_file)
    # returns a dictionary of the configuration file.

    excel_file = config.get("excel_file", "input.xlsx")
    url_column = config.get("url_column", "URL")
    output_folder = config.get("output_folder", "downloaded_images")
    max_concurrent_downloads = config.get("max_concurrent_downloads", 50)
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Initialize an error log dictionary
    error_log = {"invalid_urls": {}, "download_errors": {},
                "METADATA": {"excel_file": excel_file, "timestamp": current_time, "config": config, "notes": ""}}
    
    log_errors(error_log)

    # Run the asynchronous image download function
    asyncio.run(
        get_images(config, error_log)
    )

def get_file_extension(url, default_ext=".jpg"):
    """Returns the file extension of the URL if it's a valid image type, otherwise returns a default extension."""
    parsed_url = urlparse(url)
    path = parsed_url.path
    ext = os.path.splitext(path)[1]
    return (
        ext
        if ext in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
        else default_ext
    )

# Put in config or something later
CONSECUTIVE_FAILURE_THRESHOLD = 100
consecutive_failures = 0

async def download_image(semaphore, client, url, output, index, err_log, max_retries=3):
    """
    Downloads an image from a URL and saves it to the specified output directory.
    """
    global consecutive_failures
    async with semaphore:
        row = index + 1
        if not isinstance(url, str) or not url.startswith("http"):
            err_log["invalid_urls"][row] = url
            return

        headers = {"User-Agent": random.choice(USER_AGENTS)}
        retries = 0

        while retries < max_retries:
            try:
                response = await client.get(url, headers=headers, timeout=10)
                response.raise_for_status()

                parsed_url = urlparse(url)
                original_filename = os.path.basename(parsed_url.path)
                ext = get_file_extension(url)
                if not original_filename:
                    original_filename = f"image_{index}{ext}"

                file_path = os.path.join(output, original_filename)
                with open(file_path, "wb") as file:
                    file.write(response.content)

                # Reset consecutive failures on successful download
                consecutive_failures = 0

                # Introduce a delay to avoid being flagged as spam
                await asyncio.sleep(random.uniform(0.5, 2.0))
                break  # Exit the retry loop if the request is successful

            except httpx.HTTPStatusError as e:
                print(f"HTTP Status error occurred: {e}")
                err_log["download_errors"][row] = {"url": url, "error": str(e)}
                break  # Do not retry on HTTP status errors

            except httpx.RequestError as e:
                print(f"Request error occurred: {e}")
                err_log["download_errors"][row] = {"url": url, "error": str(e)}
                retries += 1
                if retries < max_retries:
                    wait_time = 2 ** retries  # Exponential backoff
                    print(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    print("Max retries reached. Moving to the next URL.")
                    consecutive_failures += 1

                    # Check if the consecutive failure threshold is reached
                    if consecutive_failures >= CONSECUTIVE_FAILURE_THRESHOLD:
                        print("Consecutive failure threshold reached. Stopping the program.")
                        err_log["METADATA"]["notes"] = "Consecutive failure threshold reached. Stopping the program."
                        log_errors(err_log)
                        sys.exit(1)


def log_errors(err_log):
    """Logs errors to a JSON file."""

    err_log["METADATA"]["num_urls"] = len(err_log["invalid_urls"]) + len(err_log["download_errors"])

    num_errors = len(err_log["invalid_urls"]) + len(err_log["download_errors"])

    if num_errors > 0:
        err_log["METADATA"]["num_errors"] = num_errors
        print(
            f"Errors occurred during the download process. {num_errors} errors found."
        )
        if err_log["invalid_urls"]:
            print("Invalid URLs:")
            for row, url in err_log["invalid_urls"].items():
                print(f"Row {row}: {url}")
        if err_log["download_errors"]:
            print("Download Errors:")
            for row, error_info in err_log["download_errors"].items():
                print(f"Row {row} : URL and Error \n {error_info}")

    # Determine the filename for the error log
    base_filename = "error_log.json"
    if os.path.exists(base_filename):
        timestamp = err_log["METADATA"]["timestamp"].replace(":", "-").replace(" ", "_")
        base_filename = f"error_log_{timestamp}.json"

    with open(base_filename, "w") as error_file:
        json.dump(err_log, error_file, indent=4)


async def get_images(config, err_log):
    """extracts URLs from an Excel file and calls the download_images function."""
    file_name = config["excel_file"]
    column_name = config["url_column"]
    output_dir = config["output_folder"]
    max_dls = config["max_concurrent_downloads"]

    print(f"Reading Excel file: {file_name}")
    df = pd.read_excel(file_name, sheet_name=0, usecols=[column_name])
    # with usecols we can specify the column to be read from the Excel file. Saving memory. Still returns a DataFrame. so we access the column using df[column]

    if column_name not in df.columns:
        print(f"Error: Column '{column_name}' not found in the Excel file.")
        return
    print("File read. Starting download...")

    os.makedirs(output_dir, exist_ok=True)

    semaphore = asyncio.Semaphore(max_dls)

    # Download images concurrently
    # Creating async HTTP client.
    async with httpx.AsyncClient() as client:
        # tasks[]: List comprehension to create a list of tasks to download images concurrently.
        # The download_image function is called for each URL in the DataFrame.
        tasks = [
            download_image(semaphore, client, url, output_dir, index, err_log)
            for index, url in enumerate(df[column_name])
        ]
        # for f in tqdm(): tqdm is used to display a progress bar.
        # asyncio.as_completed(tasks): Returns an iterator over the given coroutines.
        # The iterator returns futures that complete as the coroutines complete. 
        for f in tqdm(
            asyncio.as_completed(tasks), total=len(tasks), desc="Downloading images"
        ):
            await f

    log_errors(err_log)


if __name__ == "__main__":
    main()
