#!/usr/bin/env python3
"""
Convert broken Squarespace WordPress XML export to clean CSV
"""

import re
import csv
from html import unescape
from bs4 import BeautifulSoup
import sys

def clean_html(html_text):
    """Remove HTML tags and clean up text"""
    if not html_text:
        return ""

    # Parse HTML
    soup = BeautifulSoup(html_text, 'html.parser')

    # Get text and clean it up
    text = soup.get_text(separator=' ', strip=True)

    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)

    # Unescape HTML entities
    text = unescape(text)

    return text.strip()

def extract_text_between(text, start_pattern, end_pattern):
    """Extract text between two patterns"""
    match = re.search(f'{start_pattern}(.*?){end_pattern}', text, re.DOTALL)
    return match.group(1).strip() if match else ""

def parse_xml_file(filename):
    """Parse the broken XML file and extract post data"""
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split by <item> tags to get individual posts
    items = re.split(r'<item>', content)

    posts = []

    for item in items[1:]:  # Skip first empty split
        post = {}

        # Extract title
        title_match = re.search(r'<title>(.*?)</title>', item, re.DOTALL)
        if title_match:
            post['title'] = clean_html(title_match.group(1))
        else:
            # Try to extract from content or use placeholder
            post['title'] = ""

        # Extract link
        link_match = re.search(r'<link>(.*?)</link>', item, re.DOTALL)
        if link_match:
            post['link'] = link_match.group(1).strip()
        else:
            # Try to reconstruct from wp:post_name
            post_name_match = re.search(r'<wp:post_name>(.*?)</wp:post_name>', item)
            if post_name_match:
                post_name = post_name_match.group(1).strip()
                # Check if it already has /blogfeed/ prefix
                if post_name.startswith('/'):
                    post['link'] = post_name
                elif post_name.startswith('blogfeed/') or post_name.startswith('2017/'):
                    post['link'] = '/' + post_name
                else:
                    post['link'] = '/blogfeed/' + post_name
            else:
                post['link'] = ""

        # Extract post_id
        post_id_match = re.search(r'<wp:post_id>(\d+)</wp:post_id>', item)
        post['post_id'] = post_id_match.group(1) if post_id_match else ""

        # Extract post_type
        post_type_match = re.search(r'<wp:post_type>(.*?)</wp:post_type>', item)
        post['post_type'] = post_type_match.group(1) if post_type_match else ""

        # Extract post_date
        post_date_match = re.search(r'<wp:post_date>(.*?)</wp:post_date>', item)
        if post_date_match:
            post['post_date'] = post_date_match.group(1).strip()
        else:
            # Try pubDate as fallback
            pub_date_match = re.search(r'<pubDate>(.*?)</pubDate>', item)
            post['post_date'] = pub_date_match.group(1).strip() if pub_date_match else ""

        # Extract category
        category_match = re.search(r'<category[^>]*><!\[CDATA\[(.*?)\]\]></category>', item)
        post['category'] = category_match.group(1) if category_match else ""

        # Extract excerpt
        excerpt_match = re.search(r'<excerpt:encoded><!\[CDATA\[(.*?)\]\]></excerpt:encoded>', item, re.DOTALL)
        if excerpt_match:
            post['excerpt'] = clean_html(excerpt_match.group(1))
        else:
            post['excerpt'] = ""

        # Extract content
        content_match = re.search(r'<content:encoded><!\[CDATA\[(.*?)\]\]></content:encoded>', item, re.DOTALL)
        if content_match:
            full_content = clean_html(content_match.group(1))
            # Limit content to first 1000 characters for CSV
            post['content'] = full_content[:1000] + '...' if len(full_content) > 1000 else full_content
        else:
            post['content'] = ""

        # Extract attachment URL if it's an attachment
        if post['post_type'] == 'attachment':
            attachment_match = re.search(r'<wp:attachment_url>(.*?)</wp:attachment_url>', item)
            post['attachment_url'] = attachment_match.group(1) if attachment_match else ""
        else:
            post['attachment_url'] = ""

        # Only add posts with at least some data
        if post.get('post_id') or post.get('title') or post.get('link'):
            posts.append(post)

    return posts

def write_csv(posts, output_filename):
    """Write posts to CSV file"""
    fieldnames = ['post_id', 'title', 'post_type', 'post_date', 'category',
                  'link', 'excerpt', 'content', 'attachment_url']

    with open(output_filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for post in posts:
            # Ensure all fields exist
            row = {field: post.get(field, '') for field in fieldnames}
            writer.writerow(row)

    return len(posts)

def main():
    input_file = 'Squarespace-Wordpress-Export-11-20-2025.xml'
    output_file = 'squarespace-export-cleaned.csv'

    print(f"Parsing {input_file}...")
    posts = parse_xml_file(input_file)

    print(f"Found {len(posts)} posts")
    print(f"Writing to {output_file}...")

    count = write_csv(posts, output_file)

    print(f"Successfully converted {count} entries to CSV")
    print(f"Output file: {output_file}")

if __name__ == '__main__':
    main()
