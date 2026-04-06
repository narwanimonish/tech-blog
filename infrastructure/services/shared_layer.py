"""
Lambda Layer containing shared packages (common, core).
Deploy once; attach to every Lambda so handlers don't bundle a copy.
"""

from aws_cdk import aws_lambda as _lambda

from constructs import Construct


class SharedLayer(Construct):
    """A Lambda Layer that provides common and core packages."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        asset_path: str,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)
        self.layer = _lambda.LayerVersion(
            self,
            "Layer",
            code=_lambda.Code.from_asset(asset_path),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_12],
            description="Shared common + core packages for tech-blog Lambdas",
        )

    def get_layer(self) -> _lambda.ILayerVersion:
        return self.layer
