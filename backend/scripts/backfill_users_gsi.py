#!/usr/bin/env python3
"""
One-time backfill: add listPk=USER and creation_time to existing users so they
appear in UsersListByCreationTime GSI.

Usage (from repo root, AWS creds + table name):
  USERS_TABLE=tech-blog-dev-users python3 backend/scripts/backfill_users_gsi.py
  USERS_TABLE=tech-blog-dev-users python3 backend/scripts/backfill_users_gsi.py --dry-run
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone

import boto3

USERS_LIST_PK = "USER"


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill listPk/creation_time on users for GSI listing")
    parser.add_argument("--dry-run", action="store_true", help="Print changes without writing")
    args = parser.parse_args()

    table_name = os.environ.get("USERS_TABLE", "").strip()
    if not table_name:
        print("Set USERS_TABLE to the DynamoDB users table name", file=sys.stderr)
        return 1

    table = boto3.resource("dynamodb").Table(table_name)
    now = datetime.now(timezone.utc).isoformat()
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
            if item.get("listPk") == USERS_LIST_PK and item.get("creation_time"):
                continue

            user_id = item["userId"]
            expression_names = {"#listPk": "listPk"}
            expression_values = {":pk": USERS_LIST_PK}
            update_parts = ["#listPk = :pk"]

            if not item.get("creation_time"):
                expression_names["#creation_time"] = "creation_time"
                expression_values[":creation_time"] = now
                update_parts.append("#creation_time = :creation_time")

            if args.dry_run:
                print(f"Would update userId={user_id}: {', '.join(update_parts)}")
            else:
                table.update_item(
                    Key={"userId": user_id},
                    UpdateExpression=f"SET {', '.join(update_parts)}",
                    ExpressionAttributeNames=expression_names,
                    ExpressionAttributeValues=expression_values,
                )
            updated += 1

        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break

    print(f"Scanned {scanned} users; {'would update' if args.dry_run else 'updated'} {updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
