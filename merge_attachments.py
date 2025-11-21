#!/usr/bin/env python3
"""
Merge attachments into their parent posts in the CSV
"""

import csv

def merge_attachments_to_posts(input_file, output_file):
    """
    Read the CSV and merge attachments into their associated posts.
    Pattern: Attachments appear immediately before their parent post.
    """
    # Read all rows
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    merged_posts = []
    i = 0

    while i < len(rows):
        row = rows[i]

        # If this is an attachment and next item is a post, merge them
        if row['post_type'] == 'attachment' and i + 1 < len(rows):
            next_row = rows[i + 1]

            if next_row['post_type'] in ['post', 'page']:
                # Create merged post with attachment
                merged_post = {
                    'post_id': next_row['post_id'],
                    'title': next_row['title'],
                    'post_type': next_row['post_type'],
                    'post_date': next_row['post_date'],
                    'category': next_row['category'],
                    'link': next_row['link'],
                    'excerpt': next_row['excerpt'],
                    'content': next_row['content'],
                    'attachment_url': row['attachment_url'],
                    'attachment_id': row['post_id']
                }
                merged_posts.append(merged_post)
                i += 2  # Skip both attachment and post
                continue

        # If this is a post/page without preceding attachment
        if row['post_type'] in ['post', 'page']:
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
                'attachment_id': ''
            }
            merged_posts.append(merged_post)

        # Skip standalone attachments (shouldn't be any based on our analysis)
        i += 1

    # Write merged CSV
    fieldnames = ['post_id', 'title', 'post_type', 'post_date', 'category',
                  'link', 'excerpt', 'content', 'attachment_url', 'attachment_id']

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(merged_posts)

    return len(merged_posts)

def main():
    input_file = 'squarespace-export-cleaned.csv'
    output_file = 'squarespace-export-merged.csv'

    print(f"Merging attachments from {input_file}...")
    count = merge_attachments_to_posts(input_file, output_file)

    print(f"Successfully created {output_file}")
    print(f"Total posts/pages: {count}")

    # Show statistics
    with open(output_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

        with_attachments = sum(1 for r in rows if r['attachment_url'])
        without_attachments = sum(1 for r in rows if not r['attachment_url'])
        posts = sum(1 for r in rows if r['post_type'] == 'post')
        pages = sum(1 for r in rows if r['post_type'] == 'page')

    print(f"\nStatistics:")
    print(f"  Posts: {posts}")
    print(f"  Pages: {pages}")
    print(f"  With attachments: {with_attachments}")
    print(f"  Without attachments: {without_attachments}")

if __name__ == '__main__':
    main()
