#!/usr/bin/env python3
"""
Create CSV with rich text formatting preserved (without inline styles/classes)
"""

import re
import csv
from html import unescape
from bs4 import BeautifulSoup

def clean_html_preserve_formatting(html_text):
    """
    Clean HTML but preserve structural and styling tags
    Remove inline styles, classes, and unnecessary attributes
    """
    if not html_text:
        return ""

    # Parse HTML
    soup = BeautifulSoup(html_text, 'html.parser')

    # Tags to keep
    allowed_tags = {
        # Structural tags
        'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li', 'blockquote', 'div',
        # Styling tags
        'strong', 'b', 'em', 'i', 'u', 'br',
        # Links
        'a'
    }

    # First pass: Remove attributes
    for tag in soup.find_all(True):
        # Remove style and class attributes
        if 'style' in tag.attrs:
            del tag.attrs['style']
        if 'class' in tag.attrs:
            del tag.attrs['class']
        if 'data-sqsp-text-block-content' in tag.attrs:
            del tag.attrs['data-sqsp-text-block-content']
        if 'data-rte-preserve-empty' in tag.attrs:
            del tag.attrs['data-rte-preserve-empty']

        # For links, keep only href
        if tag.name == 'a' and 'href' in tag.attrs:
            href = tag.attrs['href']
            tag.attrs.clear()
            tag.attrs['href'] = href

    # Second pass: Unwrap disallowed tags (in reverse to avoid tree issues)
    tags_to_unwrap = []
    for tag in soup.find_all(True):
        if tag.name == 'span' or tag.name not in allowed_tags:
            tags_to_unwrap.append(tag)

    # Unwrap in reverse order (from leaves to root)
    for tag in reversed(tags_to_unwrap):
        try:
            tag.unwrap()
        except ValueError:
            # Tag already unwrapped or removed
            pass

    # Get the cleaned HTML
    cleaned_html = str(soup)

    # Remove the outer html/body tags that BeautifulSoup adds
    cleaned_html = re.sub(r'^<html><body>', '', cleaned_html)
    cleaned_html = re.sub(r'</body></html>$', '', cleaned_html)

    # Remove outer div wrapper if it exists
    cleaned_html = re.sub(r'^<div>\s*', '', cleaned_html)
    cleaned_html = re.sub(r'\s*</div>$', '', cleaned_html)

    # Clean up excessive whitespace but preserve single spaces
    cleaned_html = re.sub(r'\n\s*\n', '\n', cleaned_html)
    cleaned_html = cleaned_html.strip()

    return cleaned_html

def extract_content_from_xml(xml_text, start_pattern, end_pattern):
    """Extract content between two patterns"""
    match = re.search(f'{start_pattern}(.*?){end_pattern}', xml_text, re.DOTALL)
    return match.group(1).strip() if match else ""

def parse_xml_with_formatting(filename):
    """Parse XML and extract posts with rich text formatting"""
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split by <item> tags
    items = re.split(r'<item>', content)

    posts = []

    for item in items[1:]:  # Skip first empty split
        post = {}

        # Extract title
        title_match = re.search(r'<title>(.*?)</title>', item, re.DOTALL)
        post['title'] = title_match.group(1).strip() if title_match else ""

        # Extract link
        link_match = re.search(r'<link>(.*?)</link>', item, re.DOTALL)
        if link_match:
            post['link'] = link_match.group(1).strip()
        else:
            post_name_match = re.search(r'<wp:post_name>(.*?)</wp:post_name>', item)
            if post_name_match:
                post_name = post_name_match.group(1).strip()
                post['link'] = '/' + post_name if not post_name.startswith('/') else post_name
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
            pub_date_match = re.search(r'<pubDate>(.*?)</pubDate>', item)
            post['post_date'] = pub_date_match.group(1).strip() if pub_date_match else ""

        # Extract category
        category_match = re.search(r'<category[^>]*><!\[CDATA\[(.*?)\]\]></category>', item)
        post['category'] = category_match.group(1) if category_match else ""

        # Extract excerpt WITH formatting
        excerpt_match = re.search(r'<excerpt:encoded><!\[CDATA\[(.*?)\]\]></excerpt:encoded>', item, re.DOTALL)
        if excerpt_match:
            post['excerpt'] = clean_html_preserve_formatting(excerpt_match.group(1))
        else:
            post['excerpt'] = ""

        # Extract content WITH formatting
        content_match = re.search(r'<content:encoded><!\[CDATA\[(.*?)\]\]></content:encoded>', item, re.DOTALL)
        if content_match:
            post['content'] = clean_html_preserve_formatting(content_match.group(1))
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

def merge_with_attachments(posts):
    """Merge attachments that follow posts"""
    merged = []
    i = 0

    while i < len(posts):
        post = posts[i]

        if post['post_type'] in ['post', 'page']:
            # Check if next item is attachment
            if i + 1 < len(posts) and posts[i + 1]['post_type'] == 'attachment':
                attachment = posts[i + 1]
                post['attachment_url'] = attachment['attachment_url']
                post['attachment_id'] = attachment['post_id']
                i += 2
            else:
                post['attachment_url'] = ''
                post['attachment_id'] = ''
                i += 1

            merged.append(post)
        else:
            i += 1

    return merged

def write_csv_with_formatting(posts, output_filename):
    """Write posts to CSV with rich text formatting preserved"""
    fieldnames = ['post_id', 'title', 'post_type', 'post_date', 'category',
                  'link', 'excerpt_formatted', 'content_formatted',
                  'attachment_url', 'attachment_id']

    with open(output_filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for post in posts:
            row = {
                'post_id': post.get('post_id', ''),
                'title': post.get('title', ''),
                'post_type': post.get('post_type', ''),
                'post_date': post.get('post_date', ''),
                'category': post.get('category', ''),
                'link': post.get('link', ''),
                'excerpt_formatted': post.get('excerpt', ''),
                'content_formatted': post.get('content', ''),
                'attachment_url': post.get('attachment_url', ''),
                'attachment_id': post.get('attachment_id', '')
            }
            writer.writerow(row)

    return len(posts)

def main():
    input_file = 'Squarespace-Wordpress-Export-11-20-2025.xml'
    output_file = 'squarespace-export-formatted.csv'

    print(f"Parsing {input_file} with rich text formatting...\n")
    posts = parse_xml_with_formatting(input_file)

    print(f"Found {len(posts)} total entries")
    print("Merging attachments with posts...")

    merged_posts = merge_with_attachments(posts)

    print(f"Writing {len(merged_posts)} posts/pages to {output_file}...")

    count = write_csv_with_formatting(merged_posts, output_file)

    print(f"\n✓ Successfully created {output_file}")
    print(f"  Total entries: {count}")

    # Show a sample
    print("\n" + "=" * 100)
    print("\nSample content (first post):\n")
    if merged_posts:
        sample = merged_posts[0]
        print(f"Title: {sample['title']}")
        print(f"\nExcerpt (formatted):\n{sample['excerpt'][:200]}...\n")
        print(f"Content (first 500 chars formatted):\n{sample['content'][:500]}...\n")

if __name__ == '__main__':
    main()
