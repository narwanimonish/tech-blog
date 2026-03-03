from aws_cdk import (
    RemovalPolicy,
)
from aws_cdk import (
    aws_dynamodb as dynamodb,
)
from constructs import Construct


class DynamoDBTable(Construct):
    def __init__(
        self, 
        scope: Construct, 
        id: str, 
        table_name: str,
        partition_key_name: str,
        partition_key_type: dynamodb.AttributeType = dynamodb.AttributeType.STRING,
        sort_key_name: str | None = None,
        sort_key_type: dynamodb.AttributeType = dynamodb.AttributeType.STRING,
        billing_mode: dynamodb.BillingMode = dynamodb.BillingMode.PAY_PER_REQUEST,
        **kwargs
    ):
        super().__init__(scope, id)

        # Define the partition key
        partition_key = dynamodb.Attribute(
            name=partition_key_name, 
            type=partition_key_type
        )

        # Define the sort key if provided
        sort_key = None
        if sort_key_name:
            sort_key = dynamodb.Attribute(
                name=sort_key_name, 
                type=sort_key_type
            )

        self.table = dynamodb.Table(
            self, f"{id}Table",
            table_name=table_name,
            partition_key=partition_key,
            sort_key=sort_key,
            billing_mode=billing_mode,
            # Best Practice: Enable Point-in-Time Recovery for production
            # point_in_time_recovery=True,
            # Standardize removal policy (DESTROY is risky for prod, but good for dev)
            removal_policy=RemovalPolicy.DESTROY, 
            **kwargs
        )

    def get_table(self) -> dynamodb.Table:
        return self.table