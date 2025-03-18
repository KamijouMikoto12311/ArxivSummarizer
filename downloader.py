import os
import json
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import concurrent.futures


def load_config(config_path: str) -> str:
    """
    Load the advanced search URL from a JSON configuration file.
    """
    with open(config_path, "r", encoding="utf-8") as f:
        config_data = json.load(f)
    url = config_data.get("url", "").strip()
    if not url:
        raise ValueError("URL not found in configuration.")
    return url


def extract_submission_date(result) -> datetime:
    """
    Extract the submission date from an arXiv result element.

    Args:
        result: A BeautifulSoup element corresponding to a search result.

    Returns:
        A datetime object for the submission date if found; otherwise, None.
    """
    date_info = result.find("p", class_="is-size-7")
    if not date_info:
        return None

    date_text = date_info.get_text(strip=True)
    # Regex to capture a date following "Submitted", even if there's no space.
    date_pattern = r"Submitted\s*(\d{1,2}\s+\w+,\s*\d{4})"
    match = re.search(date_pattern, date_text)
    if not match:
        return None

    date_str = match.group(1)
    try:
        # Example: "4 March, 2025"
        return datetime.strptime(date_str, "%d %B, %Y")
    except ValueError:
        return None


def extract_pdf_url(result) -> str:
    """
    Extract the PDF URL from an arXiv result element.

    Args:
        result: A BeautifulSoup element corresponding to a search result.

    Returns:
        The full PDF URL as a string if found; otherwise, None.
    """
    for a in result.find_all("a"):
        href = a.get("href", "")
        if "pdf" in href.lower():
            # If the link is relative, prepend the domain.
            if not href.startswith("http"):
                return "https://arxiv.org" + href
            return href
    return None


def download_pdf(pdf_url: str, output_dir: str) -> bool:
    """
    Download the PDF from a given URL and save it to the output directory.
    """
    try:
        pdf_response = requests.get(pdf_url)
        pdf_response.raise_for_status()
    except Exception as e:
        print(f"Error downloading PDF from {pdf_url}: {e}")
        return False

    pdf_id = pdf_url.split("/")[-1]
    filename = f"{pdf_id}.pdf"
    filepath = os.path.join(output_dir, filename)

    try:
        with open(filepath, "wb") as f:
            f.write(pdf_response.content)
        print(f"Saved PDF to: {filepath}")
        return True
    except Exception as e:
        print(f"Error saving PDF {filename}: {e}")
        return False


def process_page(base_url: str, offset: int, cutoff_date: datetime, output_dir: str) -> int:
    """
    Process a single page of arXiv search results: fetch HTML, extract submission dates,
    and download PDFs for papers submitted on or after the cutoff date.

    This function downloads PDFs concurrently using a ThreadPoolExecutor.

    Args:
        base_url: The base arXiv search URL.
        offset: The pagination offset (e.g., 0 for the first page, 50 for the second).
        cutoff_date: Only download papers submitted on or after this date.
        output_dir: Directory where PDFs will be saved.

    Returns:
        The number of PDFs downloaded from this page.
    """

    paginated_url = f"{base_url}&start={offset}"
    print(f"\nFetching page: {paginated_url}")
    response = requests.get(paginated_url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    results = soup.find_all("li", class_="arxiv-result")
    print(f"Found {len(results)} results on this page.")

    download_tasks = []
    for idx, result in enumerate(results, start=1):
        submission_date = extract_submission_date(result)
        if submission_date is None:
            print(f"[Result {idx}] No submission date found; skipping.")
            continue

        print(f"[Result {idx}] Submission date: {submission_date.strftime('%Y-%m-%d')}")
        if submission_date < cutoff_date:
            print(f"[Result {idx}] Paper is older than cutoff; skipping.")
            continue

        pdf_url = extract_pdf_url(result)
        if pdf_url is None:
            print(f"[Result {idx}] No PDF URL found; skipping.")
            anchors = [a.get("href", "") for a in result.find_all("a")]
            print(f"[Result {idx}] Found anchor hrefs: {anchors}")
            continue

        print(f"[Result {idx}] Queuing PDF URL: {pdf_url}")
        download_tasks.append(pdf_url)

    download_count = 0
    if download_tasks:
        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
            futures = {executor.submit(download_pdf, url, output_dir): url for url in download_tasks}
            for future in concurrent.futures.as_completed(futures):
                if future.result():
                    download_count += 1
    return download_count


def download_pdfs(config_path: str, output_dir: str, days: int = 7, offsets=None) -> int:
    """
    Download PDFs from arXiv based on the configuration and cutoff days.

    Args:
        config_path: Path to the configuration JSON file.
        output_dir: Directory where PDFs will be saved.
        days: Only download papers submitted in the last 'days' days.
        offsets: A list of pagination offsets to process (default: [0, 50]).

    Returns:
        Total number of PDFs downloaded.
    """

    if offsets is None:
        offsets = [0, 50]
    base_url = load_config(config_path)
    os.makedirs(output_dir, exist_ok=True)
    cutoff_date = datetime.now() - timedelta(days=days)
    total_downloaded = 0
    for offset in offsets:
        total_downloaded += process_page(base_url, offset, cutoff_date, output_dir)
    print(f"\nDone! Total PDFs downloaded in '{output_dir}': {total_downloaded}.")
    return total_downloaded


# Main function for testing this module directly
def main():
    config_path = "config/url.json"
    output_dir = "downloaded_pdfs"
    days = 7  # Only download papers submitted within the last 7 days.
    download_pdfs(config_path, output_dir, days)


if __name__ == "__main__":
    main()
