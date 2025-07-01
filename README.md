# Excel URL Downloader

A Python-based tool to automate the process of downloading images (or files) from URLs listed in an Excel spreadsheet. This utility is useful for bulk-downloading assets referenced in a column of an Excel file—ideal for cataloging, archiving, or data preparation tasks.

## Features

- Reads an Excel file and fetches all URLs from a specified column.
- Downloads images/files to a local output directory.
- Handles concurrent downloads for efficiency.
- Logs invalid URLs and download errors.
- Configurable options via `config.json`.

## How It Works

1. **Configuration:**  
   Update `config.json` with your Excel file name, the column containing URLs, the output folder, and the desired concurrency.
2. **Run the Script:**  
   The script reads the Excel file, fetches URLs, and downloads each file/image to the specified folder.
3. **Error Logging:**  
   Invalid URLs and download errors are logged in `error_log.json` for troubleshooting.

## Configuration

Edit `config.json` to set up:

```json
{
    "excel_file": "Photos Merge3 4.1.24 AB.xlsx",
    "url_column": "Image URL Link",
    "output_folder": "downloaded_images",
    "max_concurrent_downloads": 25
}
```

- **excel_file:** Name/path of your Excel file.
- **url_column:** Name of the column containing the URLs.
- **output_folder:** Directory where downloaded files will be saved.
- **max_concurrent_downloads:** Controls parallel download threads.

## Usage

```bash
pip install -r requirements.txt
python main.py
```

- Make sure your Python environment has the required dependencies (`httpx`, `openpyxl`, etc.).
- The script will report invalid URLs and errors to the console and `error_log.json`.

## Error Handling

- Consecutive failed downloads are tracked; if failures exceed a threshold, the script stops for safety.
- All issues are logged for review in `error_log.json`.

## Customization

- You can adjust thresholds, timeouts, and user-agent headers in the script (`main.py`) for more advanced scenarios.
- Extend the tool to support other file types or integrate with other data sources as needed.
