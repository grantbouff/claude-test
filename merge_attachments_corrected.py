#!/usr/bin/env python3
"""
Merge attachments into posts with CORRECT alignment (attachment follows post)
and add review flags for posts that need manual checking
"""

import csv
import re
from urllib.parse import urlparse

def get_filename(url):
    """Extract clean filename from URL"""
    if not url:
        return ""
    path = urlparse(url).path
    filename = path.split('/')[-1]
    # Remove extension and parameters
    filename = re.sub(r'\.(jpg|jpeg|png|gif|webp).*$', '', filename.lower())
    return filename

def simplify_text(text):
    """Remove special chars and spaces for comparison"""
    text = re.sub(r'[^a-z0-9]', '', text.lower())
    return text

def check_match_quality(title, filename):
    """
    Determine if filename matches title and return match quality
    Returns: (match_score, needs_review, reason)
    """
    if not filename:
        return 0, True, "No image"

    # Generic/stock image names
    generic_names = [
        'blog_black', 'blog_white', 'blog_red', 'blog_blue', 'blog_green',
        'blog', 'image', 'img', 'unsplash', 'photo', 'untitled',
        'attachment', 'screen', 'title+slide', 'title'
    ]

    filename_lower = filename.lower()

    # Check if it's a generic image
    for generic in generic_names:
        if filename_lower == generic or filename_lower.startswith(generic + '_'):
            return 1, True, f"Generic image ({generic})"

    # Compare filename to title
    simple_title = simplify_text(title)
    simple_filename = simplify_text(filename)

    # Exact match
    if simple_filename in simple_title or simple_title in simple_filename:
        return 10, False, "Good match"

    # Check for partial matches (at least 5 chars)
    if len(simple_filename) >= 5:
        # Split title into words and check each
        title_words = re.findall(r'[a-z0-9]{3,}', simple_title)
        filename_words = re.findall(r'[a-z0-9]{3,}', simple_filename)

        # Count matching words
        matches = sum(1 for fw in filename_words for tw in title_words if fw in tw or tw in fw)

        if matches >= 2:
            return 8, False, "Partial match"
        elif matches >= 1:
            return 5, True, "Weak match - verify"

    # No clear match
    return 2, True, "No match - likely stock photo"

def merge_attachments_corrected(input_file, output_file):
    """
    Read CSV and merge attachments that FOLLOW their posts (corrected logic)
    """
    # Read all rows
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    merged_posts = []
    i = 0

    while i < len(rows):
        row = rows[i]

        # If this is a post or page
        if row['post_type'] in ['post', 'page']:
            # Check if NEXT item is an attachment
            if i + 1 < len(rows) and rows[i + 1]['post_type'] == 'attachment':
                next_row = rows[i + 1]

                # Create merged post with attachment from NEXT row
                attachment_url = next_row['attachment_url']
                attachment_id = next_row['post_id']
                filename = get_filename(attachment_url)

                # Check match quality
                match_score, needs_review, reason = check_match_quality(row['title'], filename)

                merged_post = {
                    'post_id': row['post_id'],
                    'title': row['title'],
                    'post_type': row['post_type'],
                    'post_date': row['post_date'],
                    'category': row['category'],
                    'link': row['link'],
                    'excerpt': row['excerpt'],
                    'content': row['content'],
                    'attachment_url': attachment_url,
                    'attachment_id': attachment_id,
                    'attachment_filename': filename,
                    'needs_review': 'YES' if needs_review else 'NO',
                    'review_reason': reason
                }
                merged_posts.append(merged_post)
                i += 2  # Skip both post and attachment
                continue
            else:
                # Post without attachment
                merged_post = {
                    'post_id': row['post_id'],
                    'title': row['title'],
                    'post_type': row['post_type'],
                    'post_date': row['post_date'],
                    'category': row['category'],
                    'link': row['link'],
                    'excerpt': row['excerpt'],
                    'content': row['content'],
                    'attachment_url': '',
                    'attachment_id': '',
                    'attachment_filename': '',
                    'needs_review': 'YES',
                    'review_reason': 'No image'
                }
                merged_posts.append(merged_post)

        # Skip standalone attachments (shouldn't happen with correct alignment)
        i += 1

    # Write merged CSV
    fieldnames = ['post_id', 'title', 'post_type', 'post_date', 'category',
                  'link', 'excerpt', 'content', 'attachment_url', 'attachment_id',
                  'attachment_filename', 'needs_review', 'review_reason']

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(merged_posts)

    return merged_posts

def print_statistics(posts):
    """Print statistics about the merged data"""
    total = len(posts)
    with_images = sum(1 for p in posts if p['attachment_url'])
    without_images = sum(1 for p in posts if not p['attachment_url'])
    needs_review = sum(1 for p in posts if p['needs_review'] == 'YES')
    good_matches = sum(1 for p in posts if p['needs_review'] == 'NO')

    # Count by review reason
    reasons = {}
    for p in posts:
        reason = p['review_reason']
        reasons[reason] = reasons.get(reason, 0) + 1

    print(f"\nStatistics:")
    print(f"  Total posts/pages: {total}")
    print(f"  With images: {with_images}")
    print(f"  Without images: {without_images}")
    print(f"  Good matches (no review needed): {good_matches}")
    print(f"  Needs manual review: {needs_review}")
    print(f"\nReview reasons:")
    for reason, count in sorted(reasons.items(), key=lambda x: -x[1]):
        print(f"  {reason}: {count}")

def show_examples(posts):
    """Show examples of different match qualities"""
    print("\n" + "=" * 100)
    print("\nGOOD MATCHES (no review needed):\n")
    good = [p for p in posts if p['needs_review'] == 'NO'][:10]
    for i, p in enumerate(good, 1):
        print(f"[{i}] Post {p['post_id']}: {p['title'][:50]}")
        print(f"    Filename: {p['attachment_filename']}")
        print(f"    Reason: {p['review_reason']}")
        print()

    print("=" * 100)
    print("\nNEEDS REVIEW (first 15):\n")
    review = [p for p in posts if p['needs_review'] == 'YES'][:15]
    for i, p in enumerate(review, 1):
        print(f"[{i}] Post {p['post_id']}: {p['title'][:50]}")
        print(f"    Filename: {p['attachment_filename'] or '(none)'}")
        print(f"    Reason: {p['review_reason']}")
        print()

def main():
    input_file = 'squarespace-export-cleaned.csv'
    output_file = 'squarespace-export-merged.csv'

    print("Merging attachments with CORRECTED alignment...")
    print("(Attachments follow their posts, not precede them)\n")

    merged_posts = merge_attachments_corrected(input_file, output_file)

    print(f"\n✓ Successfully created {output_file}")

    print_statistics(merged_posts)
    show_examples(merged_posts)

if __name__ == '__main__':
    main()
