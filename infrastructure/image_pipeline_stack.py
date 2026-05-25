"""CDK stack defining every AWS resource the image pipeline uses.

Creates the S3 buckets, the SQS queues, the DynamoDB table, and the Lambda
worker, wires them together with least-privilege permissions, and outputs the
names the submitter needs.
"""
from pathlib import Path

import aws_cdk as cdk
from aws_cdk import Duration, RemovalPolicy, Stack
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_ecr_assets as ecr_assets
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_lambda_event_sources as event_sources
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_sqs as sqs
from constructs import Construct

# Repository root, used as the Docker build context for the worker image.
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class ImagePipelineStack(Stack):
    """All resources for the distributed image-processing pipeline."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Storage. DESTROY and auto_delete let the environment be torn down
        # cleanly after the evaluation; a production stack would retain data.
        input_bucket = s3.Bucket(
            self,
            "InputBucket",
            encryption=s3.BucketEncryption.S3_MANAGED,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )
        output_bucket = s3.Bucket(
            self,
            "OutputBucket",
            encryption=s3.BucketEncryption.S3_MANAGED,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # Metadata store, keyed on the image id so writes are idempotent.
        metadata_table = dynamodb.Table(
            self,
            "MetadataTable",
            partition_key=dynamodb.Attribute(
                name="imageId", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Queues. The visibility timeout is six times the function timeout; a
        # message moves to the dead-letter queue after five failed receives.
        dead_letter_queue = sqs.Queue(
            self, "DeadLetterQueue", retention_period=Duration.days(14)
        )
        work_queue = sqs.Queue(
            self,
            "WorkQueue",
            visibility_timeout=Duration.seconds(720),
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=5, queue=dead_letter_queue
            ),
        )

        # Worker: a Lambda function built from the Dockerfile at the repo root.
        # The function and image are both arm64; the two must match or Lambda
        # cannot start the container. No reserved concurrency is set, so the
        # function scales within the account's concurrency limit.
        worker = lambda_.DockerImageFunction(
            self,
            "Worker",
            code=lambda_.DockerImageCode.from_image_asset(
                str(PROJECT_ROOT),
                platform=ecr_assets.Platform.LINUX_ARM64,
            ),
            architecture=lambda_.Architecture.ARM_64,
            memory_size=2048,
            timeout=Duration.seconds(120),
            environment={
                "INPUT_BUCKET": input_bucket.bucket_name,
                "OUTPUT_BUCKET": output_bucket.bucket_name,
                "METADATA_TABLE": metadata_table.table_name,
                "WATERMARK": "false",
            },
        )

        # Trigger the worker from the queue, one image per invocation. This
        # also grants the worker permission to consume from the queue.
        worker.add_event_source(
            event_sources.SqsEventSource(work_queue, batch_size=1)
        )

        # Least-privilege permissions.
        input_bucket.grant_read(worker)
        output_bucket.grant_write(worker)
        metadata_table.grant_write_data(worker)

        # Outputs: the names the submitter needs.
        cdk.CfnOutput(self, "InputBucketName", value=input_bucket.bucket_name)
        cdk.CfnOutput(self, "OutputBucketName", value=output_bucket.bucket_name)
        cdk.CfnOutput(self, "WorkQueueUrl", value=work_queue.queue_url)
        cdk.CfnOutput(self, "MetadataTableName", value=metadata_table.table_name)
