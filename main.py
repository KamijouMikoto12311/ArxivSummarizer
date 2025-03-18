import os
from datetime import datetime

from downloader import download_pdfs
from SiliconFlow import process_pdfs_in_directory


def main():
    # Download pdfs
    config_path = "config/url.json"
    output_dir = "data/downloaded_pdfs"
    days = 7
    download_pdfs(config_path, output_dir, days)

    # Process with LLM
    pdf_directory = os.path.abspath(output_dir)

    output_directory = os.path.join(os.getcwd(), "summary/")
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    output_name = f"summary-{datetime.now().strftime('%Y-%m-%d')}.txt"

    processed_dir_acs = "data/summarized_pdfs"

    with open("config/api.txt", "r") as f:
        lines = f.readlines()
    api_key = lines[0]

    num_try = 0
    patience = 5
    while os.listdir(pdf_directory) and num_try < patience:
        num_try += 1
        process_pdfs_in_directory(pdf_directory, processed_dir_acs, api_key, output_directory, output_name=output_name)


if __name__ == "__main__":
    main()
