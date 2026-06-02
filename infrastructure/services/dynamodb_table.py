from aws_cdk import (
    RemovalPolicy,
    aws_dynamodb as dynamodb,
)

from constructs import Construct


class GlobalSecondaryIndexSpec:
    """Declarative GSI for DynamoDBTable."""

    def __init__(
        self,
        index_name: str,
        partition_key_name: str,
        *,
        partition_key_type: dynamodb.AttributeType = dynamodb.AttributeType.STRING,
        sort_key_name: str | None = None,
        sort_key_type: dynamodb.AttributeType = dynamodb.AttributeType.STRING,
        projection_type: dynamodb.ProjectionType = dynamodb.ProjectionType.ALL,
    ):
        self.index_name = index_name
        self.partition_key_name = partition_key_name
        self.partition_key_type = partition_key_type
        self.sort_key_name = sort_key_name
        self.sort_key_type = sort_key_type
        self.projection_type = projection_type


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
        global_secondary_indexes: list[GlobalSecondaryIndexSpec] | None = None,
        **kwargs,
    ):
        super().__init__(scope, id)

        # Define the partition key
        partition_key = dynamodb.Attribute(name=partition_key_name, type=partition_key_type)

        # Define the sort key if provided
        sort_key = None
        if sort_key_name:
            sort_key = dynamodb.Attribute(name=sort_key_name, type=sort_key_type)

        gsi_props = []
        for gsi in global_secondary_indexes or []:
            gsi_partition = dynamodb.Attribute(name=gsi.partition_key_name, type=gsi.partition_key_type)
            gsi_sort = None
            if gsi.sort_key_name:
                gsi_sort = dynamodb.Attribute(name=gsi.sort_key_name, type=gsi.sort_key_type)
            gsi_props.append(
                dynamodb.GlobalSecondaryIndexProps(
                    index_name=gsi.index_name,
                    partition_key=gsi_partition,
                    sort_key=gsi_sort,
                    projection_type=gsi.projection_type,
                )
            )

        self.table = dynamodb.Table(
            self,
            f"{id}Table",
            table_name=table_name,
            partition_key=partition_key,
            sort_key=sort_key,
            billing_mode=billing_mode,
            global_secondary_indexes=gsi_props or None,
            # Best Practice: Enable Point-in-Time Recovery for production
            # point_in_time_recovery=True,
            # Standardize removal policy (DESTROY is risky for prod, but good for dev)
            removal_policy=RemovalPolicy.DESTROY,
            **kwargs,
        )

    def get_table(self) -> dynamodb.Table:
        return self.table
