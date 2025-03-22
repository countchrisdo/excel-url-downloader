"""
This script downloads images from URLs listed in an Excel file."
"""
import os
import json
# import time
from urllib.parse import urlparse
import pandas as pd
import requests
from tqdm import tqdm  # Add this import


def get_file_extension(url, default_ext=".jpg"):
    parsed_url = urlparse(url)
    path = parsed_url.path
    ext = os.path.splitext(path)[1]
    return ext if ext in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"} else default_ext


def download_images_from_excel(file, column, output):
    """
    Args:
        file (str): The path to the Excel file containing the URLs.
        column (str): The name of the column in the Excel file that contains the URLs.
        output (str): The directory where the downloaded images will be saved.

    Returns:
        None

    Notes:
        - Only URLs starting with 'http' are considered valid.
        - The function will skip invalid URLs and print a message for each skipped URL.
    """
    #init
    df = pd.read_excel(file)
    # Create an error log dictionary
    error_log = {
        "invalid_urls": [],
        "download_errors": []
    }
    
    if column not in df.columns:
        print(f"Error: Column '{column}' not found in the Excel file.")
        return
    
    # Create the output folder if it doesn't exist
    os.makedirs(output, exist_ok=True)
    
    for index, url in tqdm(enumerate(df[column]), total=len(df[column]), desc="Downloading images"):
        if not isinstance(url, str) or not url.startswith("http"):
            # print(f"Skipping invalid URL at row {index + 1}: {url}")
            error_log["invalid_urls"].append(f"- Row: {index+1} | URL: {url}")
            continue
        
        try:
            # Send a GET request to the URL
            # Use stream=True for large files
            response = requests.get(url, stream=False, timeout=10)
            response.raise_for_status()

            # extract filename from URL
            parsed_url = urlparse(url)
            original_filename = os.path.basename(parsed_url.path)
            ext = get_file_extension(url)
            # if filename is empty, use a default name
            if not original_filename:
                original_filename = f"image_{index}{ext}"

            file_path = os.path.join(output, original_filename)
            
            with open(file_path, "wb") as file:
                for chunk in response.iter_content(1024):
                    file.write(chunk)
            
            # print for debug but it lowers performance
            # print(f"Downloaded: {filename}")
        except requests.exceptions.RequestException as e:
            print(f"Failed to download {url}: {e}")
            error_log["download_errors"].append(f"Failed to download {url}: {e}")
    # if error log is not empty, print the errors
    num_errors = len(error_log["invalid_urls"]) + len(error_log["download_errors"])
    if num_errors > 0:
        print(f"Errors occurred during the download process. {num_errors} errors found.")
        if error_log["invalid_urls"]:
            print("Invalid URLs:")
            for error in error_log["invalid_urls"]:
                print(error)
        if error_log["download_errors"]:
            print("Download Errors:")
            for error in error_log["download_errors"]:
                print(error)
    # save error log to a file
    with open("error_log.json", "w") as error_file:
        json.dump(error_log, error_file, indent=4)


if __name__ == "__main__":
    # start_time = time.time()
    print("Starting the image download process...")
    # Load configuration from config.json
    with open("config.json", "r") as config_file:
        config = json.load(config_file)

    # Get configuration values
    # Set default values if not provided in config
    excel_file = config.get("excel_file", "input.xlsx")
    url_column = config.get("url_column", "URL")
    output_folder = config.get("output_folder", "downloaded_images")
    
    download_images_from_excel(excel_file, url_column, output_folder)
    # end_time = time.time()
    # elapsed_time = end_time - start_time
    # print(f"Image download process completed in {elapsed_time:.2f} seconds.")
