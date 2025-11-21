#!/usr/bin/env python3
"""
Scrape actual blog post pages to get correct header images - improved version
"""

import csv
import time
import sys
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

def create_session():
    """
    Create a requests session with retry logic and realistic headers
    """
    session = requests.Session()

    # Add retry strategy
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    # More realistic headers
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    })

    return session

def get_header_image(session, url, verbose=True):
    """
    Fetch a blog post URL and extract the header/featured image
    """
    try:
        # Add delay to be polite
        time.sleep(1)

        response = session.get(url, timeout=15, allow_redirects=True)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Try multiple methods to find the header/featured image

        # Method 1: Look for Squarespace featured image in blog post header
        selectors = [
            '.blog-item-top-wrapper img',
            'article .image-block img',
            '.blog-item-wrapper .sqs-block-image img',
            '.BlogItem-image img',
            'figure.blog-item-top-wrapper img',
            '.entry-header img',
            '.sqs-block-image-figure img'
        ]

        for selector in selectors:
            img = soup.select_one(selector)
            if img:
                # Try data-src first (lazy loading), then src
                img_url = img.get('data-src') or img.get('data-image') or img.get('src')
                if img_url:
                    # Make sure it's a full URL
                    if img_url.startswith('//'):
                        img_url = 'https:' + img_url
                    elif img_url.startswith('/'):
                        img_url = urljoin(url, img_url)

                    # Filter out tiny images (icons, logos, etc)
                    if 'logo' not in img_url.lower() and 'icon' not in img_url.lower():
                        return img_url

        # Method 2: Check meta tags for featured image
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            return og_image['content']

        twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})
        if twitter_image and twitter_image.get('content'):
            return twitter_image['content']

        return None

    except requests.HTTPError as e:
        if verbose:
            print(f"  ⚠️  HTTP Error {e.response.status_code}")
        return None
    except requests.RequestException as e:
        if verbose:
            print(f"  ⚠️  Connection error: {str(e)[:100]}")
        return None
    except Exception as e:
        if verbose:
            print(f"  ⚠️  Parse error: {str(e)[:100]}")
        return None

def update_csv_with_real_images(input_file, output_file):
    """
    Read CSV, fetch real images from live pages, update CSV
    """
    base_url = "https://www.thepointva.com"

    # Read input CSV
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Filter to only posts
    posts = [r for r in rows if r['post_type'] == 'post']

    print(f"Processing {len(posts)} blog posts (out of {len(rows)} total entries)...")
    print("=" * 80)

    session = create_session()
    updated_count = 0
    skipped_count = 0

    for i, row in enumerate(rows, 1):
        # Only process posts (not pages)
        if row['post_type'] != 'post':
            continue

        link = row['link']
        if not link:
            skipped_count += 1
            continue

        # Construct full URL
        full_url = urljoin(base_url, link)

        print(f"\n[{i}/{len(rows)}] {row['title'][:60]}")
        print(f"  {full_url}")

        # Get the header image
        image_url = get_header_image(session, full_url)

        if image_url:
            row['attachment_url'] = image_url
            print(f"  ✓ {image_url[:80]}...")
            updated_count += 1
        else:
            row['attachment_url'] = ''
            row['attachment_id'] = ''
            print(f"  ○ No image")
            skipped_count += 1

        # Progress indicator
        if i % 10 == 0:
            print(f"\n--- Progress: {i}/{len(rows)} | Found: {updated_count} | Skipped: {skipped_count} ---")

    # Write updated CSV
    fieldnames = ['post_id', 'title', 'post_type', 'post_date', 'category',
                  'link', 'excerpt', 'content', 'attachment_url', 'attachment_id']

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("\n" + "=" * 80)
    print(f"\n✓ Successfully created {output_file}")
    print(f"\nStatistics:")
    print(f"  Total entries: {len(rows)}")
    print(f"  Posts processed: {len(posts)}")
    print(f"  Images found: {updated_count}")
    print(f"  No image: {skipped_count}")

def main():
    input_file = 'squarespace-export-merged.csv'
    output_file = 'squarespace-export-with-images.csv'

    print("Scraping blog posts for header images...")
    print("This will take several minutes (1 second delay per post)...\n")

    update_csv_with_real_images(input_file, output_file)

if __name__ == '__main__':
    main()
