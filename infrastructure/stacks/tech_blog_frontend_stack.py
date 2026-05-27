"""
Static frontend: S3 + CloudFront. Deploy after API stack (needs ApiUrl for runtime config.json).
"""

from __future__ import annotations

from aws_cdk import (
    CfnOutput,
    Duration,
    Fn,
    RemovalPolicy,
    Stack,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_iam as iam,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    custom_resources as cr,
)

from config.dev import DevConfig
from config.prod import ProdConfig
from constructs import Construct


class TechBlogFrontendStack(Stack):
    """Host the React SPA on S3 behind CloudFront."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        config: DevConfig | ProdConfig,
        api_url_export_name: str,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)
        app_name = config.APP_NAME
        api_url = Fn.import_value(api_url_export_name)
        config_body = Fn.join("", ['{"apiUrl":"', api_url, '"}'])

        website_bucket = s3.Bucket(
            self,
            "WebsiteBucket",
            bucket_name=None,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        origin_access_identity = cloudfront.OriginAccessIdentity(
            self,
            "OriginAccessIdentity",
            comment=f"{app_name} frontend OAI",
        )
        website_bucket.grant_read(origin_access_identity)

        distribution = cloudfront.Distribution(
            self,
            "Distribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3Origin(
                    website_bucket,
                    origin_access_identity=origin_access_identity,
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD,
                cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD,
            ),
            default_root_object="index.html",
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.minutes(5),
                ),
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.minutes(5),
                ),
            ],
        )

        website_deployment = s3deploy.BucketDeployment(
            self,
            "DeployWebsite",
            sources=[s3deploy.Source.asset("../ui/dist")],
            destination_bucket=website_bucket,
            distribution=distribution,
            distribution_paths=["/*"],
        )

        # BucketDeployment json_data cannot use Fn::ImportValue; write config at deploy time instead.
        write_config = cr.AwsCustomResource(
            self,
            "WriteRuntimeConfig",
            on_create=cr.AwsSdkCall(
                service="S3",
                action="putObject",
                parameters={
                    "Bucket": website_bucket.bucket_name,
                    "Key": "config.json",
                    "Body": config_body,
                    "ContentType": "application/json",
                    "CacheControl": "no-cache, no-store, must-revalidate",
                },
                physical_resource_id=cr.PhysicalResourceId.of(f"{app_name}-runtime-config"),
            ),
            on_update=cr.AwsSdkCall(
                service="S3",
                action="putObject",
                parameters={
                    "Bucket": website_bucket.bucket_name,
                    "Key": "config.json",
                    "Body": config_body,
                    "ContentType": "application/json",
                    "CacheControl": "no-cache, no-store, must-revalidate",
                },
                physical_resource_id=cr.PhysicalResourceId.of(f"{app_name}-runtime-config"),
            ),
            policy=cr.AwsCustomResourcePolicy.from_statements(
                [
                    iam.PolicyStatement(
                        actions=["s3:PutObject"],
                        resources=[website_bucket.arn_for_objects("config.json")],
                    ),
                ]
            ),
        )
        write_config.node.add_dependency(website_deployment)

        invalidate_config = cr.AwsCustomResource(
            self,
            "InvalidateConfigCache",
            on_create=cr.AwsSdkCall(
                service="CloudFront",
                action="createInvalidation",
                parameters={
                    "DistributionId": distribution.distribution_id,
                    "InvalidationBatch": {
                        "CallerReference": Fn.join("-", [app_name, "config", api_url]),
                        "Paths": {"Quantity": 1, "Items": ["/config.json"]},
                    },
                },
                physical_resource_id=cr.PhysicalResourceId.from_response("Invalidation.Id"),
            ),
            on_update=cr.AwsSdkCall(
                service="CloudFront",
                action="createInvalidation",
                parameters={
                    "DistributionId": distribution.distribution_id,
                    "InvalidationBatch": {
                        "CallerReference": Fn.join("-", [app_name, "config", api_url]),
                        "Paths": {"Quantity": 1, "Items": ["/config.json"]},
                    },
                },
                physical_resource_id=cr.PhysicalResourceId.from_response("Invalidation.Id"),
            ),
            policy=cr.AwsCustomResourcePolicy.from_sdk_calls(
                resources=cr.AwsCustomResourcePolicy.ANY_RESOURCE
            ),
        )
        invalidate_config.node.add_dependency(write_config)

        self.distribution = distribution
        self.frontend_url = f"https://{distribution.distribution_domain_name}"

        CfnOutput(
            self,
            "FrontendUrl",
            value=self.frontend_url,
            description="CloudFront URL for the tech-blog UI",
        )
        CfnOutput(
            self,
            "WebsiteBucketName",
            value=website_bucket.bucket_name,
            description="S3 bucket backing the frontend",
        )
