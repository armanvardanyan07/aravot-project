import argparse
import csv
import html as html_lib
import math
import random
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE_URL = "https://www.aravot.am/category/news/{slug}/"
USER_AGENT = "Mozilla/5.0"


@dataclass(frozen=True)
class Category:
    label: str
    slug: str


CATEGORIES = [
    Category("politics", "politics"),
    Category("sport", "sport"),
]


def normalize_text(text):
    return re.sub(r"\s+", " ", text).strip()


def fetch(url, timeout=30):
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def category_page_url(slug, page):
    if page == 1:
        return BASE_URL.format(slug=slug)
    return f"{BASE_URL.format(slug=slug)}page/{page}/"


def extract_category_titles(html):
    h1_match = re.search(r"<h1\b[^>]*class=\"[^\"]*\bsection_title\b[^\"]*\"", html)
    if not h1_match:
        return []

    section = html[h1_match.start():]
    sidebar_match = re.search(r"<div\s+class=\"col-md-4\"", section)
    if sidebar_match:
        section = section[: sidebar_match.start()]

    items = []
    for match in re.finditer(r"<a\b[^>]*>", section, re.IGNORECASE):
        tag = match.group(0)
        if not re.search(r"\brel=\"bookmark\"", tag, re.IGNORECASE):
            continue
        href_match = re.search(
            r"\bhref=\"(https://www\.aravot\.am/\d{4}/\d{2}/\d{2}/\d+/?)\"",
            tag,
            re.IGNORECASE,
        )
        title_match = re.search(r"\btitle=\"([^\"]+)\"", tag, re.IGNORECASE)
        if not href_match or not title_match:
            continue
        title = normalize_text(html_lib.unescape(title_match.group(1)))
        href = html_lib.unescape(href_match.group(1))
        if title:
            items.append((title, href))
    return items


def fetch_category_page(category, page):
    url = category_page_url(category.slug, page)
    try:
        html = fetch(url)
    except HTTPError as exc:
        if exc.code == 404:
            return page, []
        raise
    except URLError as exc:
        raise RuntimeError(f"Failed to fetch {url}: {exc}") from exc
    return page, extract_category_titles(html)


def collect_titles(category, limit, workers, pages_per_batch):
    titles = []
    seen_titles = set()
    seen_urls = set()
    page = 1
    empty_pages = 0

    while len(titles) < limit:
        pages = list(range(page, page + pages_per_batch))
        page += pages_per_batch
        batch_results = {}

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(fetch_category_page, category, page_number) for page_number in pages]
            for future in as_completed(futures):
                page_number, items = future.result()
                batch_results[page_number] = items

        batch_added = 0
        for page_number in sorted(batch_results):
            added = 0
            for title, article_url in batch_results[page_number]:
                if article_url in seen_urls or title in seen_titles:
                    continue
                seen_urls.add(article_url)
                seen_titles.add(title)
                titles.append(title)
                added += 1
                batch_added += 1
                if len(titles) >= limit:
                    break

            print(f"{category.label}: page {page_number}, +{added}, total {len(titles)}")
            if len(titles) >= limit:
                break

        if batch_added == 0:
            empty_pages += 1
            if empty_pages >= 2:
                break
        else:
            empty_pages = 0

    return titles[:limit]


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["category", "text"])
        writer.writeheader()
        writer.writerows(rows)


def split_rows(label, titles, test_ratio, seed):
    rows = [{"category": label, "text": title} for title in titles]
    random.Random(seed).shuffle(rows)
    test_count = max(1, round(len(rows) * test_ratio)) if rows else 0
    return rows[test_count:], rows[:test_count]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=5000)
    parser.add_argument("--test-ratio", type=float, default=0.2)
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--pages-per-batch", type=int, default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", default="data")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    pages_per_batch = args.pages_per_batch or args.workers * 4
    pages_per_batch = max(args.workers, pages_per_batch)

    all_train_rows = []
    all_test_rows = []

    for category in CATEGORIES:
        expected_pages = math.ceil(args.limit / 10)
        print(
            f"{category.label}: target={args.limit}, about {expected_pages} pages, "
            f"workers={args.workers}, batch={pages_per_batch}"
        )
        titles = collect_titles(category, args.limit, args.workers, pages_per_batch)
        train_rows, test_rows = split_rows(category.label, titles, args.test_ratio, args.seed)
        all_train_rows.extend(train_rows)
        all_test_rows.extend(test_rows)

    random.Random(args.seed).shuffle(all_train_rows)
    random.Random(args.seed).shuffle(all_test_rows)
    write_csv(output_dir / "train.csv", all_train_rows)
    write_csv(output_dir / "test.csv", all_test_rows)

    print(f"train: {len(all_train_rows)}")
    print(f"test: {len(all_test_rows)}")


if __name__ == "__main__":
    main()
