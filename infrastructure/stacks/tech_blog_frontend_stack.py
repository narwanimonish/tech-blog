"""
Static frontend: S3 + CloudFront.

Upload ui/dist after deploy (see scripts/deploy-frontend.sh and CI).
CDK only provisions the bucket and distribution — avoids BucketDeployment asset failures.
"""

from __future__ import annotations

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_s3 as s3,
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
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)
        app_name = config.APP_NAME

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

        self.distribution = distribution
        self.website_bucket = website_bucket
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
        CfnOutput(
            self,
            "DistributionId",
            value=distribution.distribution_id,
            description="CloudFront distribution ID (for cache invalidation)",
        )
