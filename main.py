"""This script downloads images from URLs listed in an Excel file.

It handles concurrent downloads, logs errors, and saves the images in a specified output directory.

It uses asyncio for concurrent downloads and httpx for making HTTP requests."""

import os
import json
import asyncio
from urllib.parse import urlparse
import httpx
import pandas as pd
from tqdm import tqdm


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


async def download_image(semaphore, client, url, output, index, err_log):
    """
    Downloads an image from a URL and saves it to the specified output directory.

    Args:
        semaphore (asyncio.Semaphore): Semaphore to limit concurrent downloads.
        client (httpx.AsyncClient): HTTP client for making requests.
        url (str): URL of the image to download.
        output (str): Directory to save the downloaded image.
        index (int): Index of the URL in the list for logging purposes.
        error_log (dict): Dictionary to log errors.

    Returns:
        None
    """
    async with semaphore:
        row = index + 1
        if not isinstance(url, str) or not url.startswith("http"):
            err_log["invalid_urls"][row] = url
            return

        try:
            response = await client.get(url, timeout=10)
            response.raise_for_status()

            parsed_url = urlparse(url)
            original_filename = os.path.basename(parsed_url.path)
            ext = get_file_extension(url)
            if not original_filename:
                original_filename = f"image_{index}{ext}"

            file_path = os.path.join(output, original_filename)
            with open(file_path, "wb") as file:
                file.write(response.content)
        except httpx.HTTPStatusError as e:
            print(f"HTTP Status error occurred: {e}")
            err_log["download_errors"][row] = {"url": url, "error": str(e)}
        except httpx.RequestError as e:
            print(f"Request error occurred: {e}")
            err_log["download_errors"][row] = {"url": url, "error": str(e)}


def log_errors(err_log):
    """Logs errors to a JSON file."""
    num_errors = len(err_log["invalid_urls"]) + len(err_log["download_errors"])

    if num_errors > 0:
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

    with open("error_log.json", "w") as error_file:
        json.dump(err_log, error_file, indent=4)


async def get_images(file, column, output, max_dls, err_log):
    """extracts URLs from an Excel file and calls the download_images function."""
    df = pd.read_excel(file)

    if column not in df.columns:
        print(f"Error: Column '{column}' not found in the Excel file.")
        return

    os.makedirs(output, exist_ok=True)

    semaphore = asyncio.Semaphore(max_dls)

    async with httpx.AsyncClient() as client:
        tasks = [
            download_image(semaphore, client, url, output, index, err_log)
            for index, url in enumerate(df[column])
        ]
        for f in tqdm(
            asyncio.as_completed(tasks), total=len(tasks), desc="Downloading images"
        ):
            await f

    log_errors(err_log)


if __name__ == "__main__":
    print("Starting the image download process...")
    with open("config.json", "r") as config_file:
        config = json.load(config_file)

    excel_file = config.get("excel_file", "input.xlsx")
    url_column = config.get("url_column", "URL")
    output_folder = config.get("output_folder", "downloaded_images")
    max_concurrent_downloads = config.get("max_concurrent_downloads", 100)

    # Initialize an error log dictionary
    error_log = {"invalid_urls": {}, "download_errors": {}}

    asyncio.run(
        get_images(
            excel_file, url_column, output_folder, max_concurrent_downloads, error_log
        )
    )
