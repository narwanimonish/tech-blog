#!/usr/bin/env python3
"""
One-time backfill: add listPk=POST to existing posts so they appear in PostsListByCreationTime GSI.

Usage (from repo root, AWS creds + table name):
  POSTS_TABLE=tech-blog-dev-posts python3 backend/scripts/backfill_posts_gsi.py
  POSTS_TABLE=tech-blog-dev-posts python3 backend/scripts/backfill_posts_gsi.py --dry-run
"""

from __future__ import annotations

import argparse
import os
import sys

import boto3

POSTS_LIST_PK = "POST"


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill listPk on posts for GSI listing")
    parser.add_argument("--dry-run", action="store_true", help="Print changes without writing")
    args = parser.parse_args()

    table_name = os.environ.get("POSTS_TABLE", "").strip()
    if not table_name:
        print("Set POSTS_TABLE to the DynamoDB posts table name", file=sys.stderr)
        return 1

    table = boto3.resource("dynamodb").Table(table_name)
    updated = 0
    scanned = 0
    last_key = None

    while True:
        scan_kwargs: dict = {}
        if last_key:
            scan_kwargs["ExclusiveStartKey"] = last_key
        response = table.scan(**scan_kwargs)
        for item in response.get("Items", []):
            scanned += 1
            if item.get("listPk") == POSTS_LIST_PK:
                continue
            if not item.get("creation_time"):
                print(f"Skip postId={item.get('postId')}: missing creation_time", file=sys.stderr)
                continue
            post_id = item["postId"]
            if args.dry_run:
                print(f"Would set listPk on postId={post_id}")
            else:
                table.update_item(
                    Key={"postId": post_id},
                    UpdateExpression="SET listPk = :pk",
                    ExpressionAttributeValues={":pk": POSTS_LIST_PK},
                )
            updated += 1
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break

    print(f"Scanned {scanned} posts; {'would update' if args.dry_run else 'updated'} {updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
