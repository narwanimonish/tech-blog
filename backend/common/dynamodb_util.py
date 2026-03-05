"""
DynamoDB helpers for simple CRUD operations.
Accepts a boto3 DynamoDB Table resource (e.g. dynamodb_resource.Table(name)).
"""
import logging

LOGGER = logging.getLogger(__name__)


def get_item(table, key):
    """
    Get a single item by partition key (and optional sort key).

    :param table: boto3 DynamoDB Table resource
    :param key: dict, e.g. {"userId": "user-001"} or {"postId": "abc", "sortKey": "xyz"}
    :return: Item dict if found, else None
    """
    try:
        response = table.get_item(Key=key)
        return response.get("Item")
    except Exception as e:
        LOGGER.exception("dynamodb_util.get_item failed: %s", e)
        raise


def put_item(table, item):
    """
    Put an item (create or overwrite).

    :param table: boto3 DynamoDB Table resource
    :param item: dict, must include partition key (and sort key if table has one)
    """
    try:
        table.put_item(Item=item)
    except Exception as e:
        LOGGER.exception("dynamodb_util.put_item failed: %s", e)
        raise


def delete_item(table, key):
    """
    Delete an item by key.

    :param table: boto3 DynamoDB Table resource
    :param key: dict, e.g. {"userId": "user-001"}
    """
    try:
        table.delete_item(Key=key)
    except Exception as e:
        LOGGER.exception("dynamodb_util.delete_item failed: %s", e)
        raise


def scan_all(table):
    """
    Scan the entire table with automatic pagination.

    :param table: boto3 DynamoDB Table resource
    :return: list of item dicts
    """
    try:
        items = []
        response = table.scan()
        items.extend(response.get("Items", []))
        while "LastEvaluatedKey" in response:
            response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(response.get("Items", []))
        return items
    except Exception as e:
        LOGGER.exception("dynamodb_util.scan_all failed: %s", e)
        raise
