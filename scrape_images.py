#!/usr/bin/env python3
"""
Scrape actual blog post pages to get correct header images
"""

import csv
import time
import re
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

def get_header_image(url):
    """
    Fetch a blog post URL and extract the header/featured image
    """
    try:
        # Add delay to be polite
        time.sleep(0.5)

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Try multiple methods to find the header/featured image

        # Method 1: Look for Squarespace featured image in blog post header
        header_img = soup.select_one('.blog-item-top-wrapper img')
        if header_img and header_img.get('data-src'):
            return header_img['data-src']
        if header_img and header_img.get('src'):
            return header_img['src']

        # Method 2: Look for main content image
        content_img = soup.select_one('article img, .sqs-block-image img')
        if content_img and content_img.get('data-src'):
            return content_img['data-src']
        if content_img and content_img.get('src'):
            return content_img['src']

        # Method 3: Look for any prominent image in the blog
        any_img = soup.select_one('.blog-item-content-wrapper img')
        if any_img and any_img.get('data-src'):
            return any_img['data-src']
        if any_img and any_img.get('src'):
            return any_img['src']

        # Method 4: Check meta tags for featured image
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            return og_image['content']

        return None

    except requests.RequestException as e:
        print(f"  ⚠️  Error fetching {url}: {e}")
        return None
    except Exception as e:
        print(f"  ⚠️  Error parsing {url}: {e}")
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

    print(f"Processing {len(rows)} entries...")
    print("=" * 80)

    updated_count = 0
    skipped_count = 0
    error_count = 0

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

        print(f"\n[{i}/{len(rows)}] Fetching: {row['title'][:50]}...")
        print(f"  URL: {full_url}")

        # Get the header image
        image_url = get_header_image(full_url)

        if image_url:
            # Clean up the image URL (remove query params for cleaner URL)
            # But keep format param if it exists
            row['attachment_url'] = image_url
            print(f"  ✓ Found image: {image_url[:80]}...")
            updated_count += 1
        else:
            row['attachment_url'] = ''
            row['attachment_id'] = ''
            print(f"  ○ No header image found")
            skipped_count += 1

    # Write updated CSV
    fieldnames = ['post_id', 'title', 'post_type', 'post_date', 'category',
                  'link', 'excerpt', 'content', 'attachment_url', 'attachment_id']

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("\n" + "=" * 80)
    print(f"\n✓ Successfully updated {output_file}")
    print(f"\nStatistics:")
    print(f"  Total entries: {len(rows)}")
    print(f"  Images found: {updated_count}")
    print(f"  No image: {skipped_count}")
    print(f"  Errors: {error_count}")

def main():
    input_file = 'squarespace-export-merged.csv'
    output_file = 'squarespace-export-with-images.csv'

    print("Scraping real blog post pages for header images...")
    print("This may take a few minutes...\n")

    update_csv_with_real_images(input_file, output_file)

if __name__ == '__main__':
    main()
