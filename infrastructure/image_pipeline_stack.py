"""The AWS CDK stack: every resource the image-processing system uses.

See design document Sections 4.2 and 11. The stack creates the S3 buckets,
the SQS queues, the DynamoDB table, and the Lambda worker, wires them
together with least-privilege permissions, and prints the values the
submitter needs in order to send work.
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

# The repository root, which is the Docker build context for the worker image.
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class ImagePipelineStack(Stack):
    """All resources for the distributed image-processing pipeline."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # --- Storage -------------------------------------------------------
        # Input and output buckets. RemovalPolicy.DESTROY with
        # auto_delete_objects lets the whole environment be torn down cleanly
        # after the evaluation; a production system would retain the data.
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

        # --- Metadata store ------------------------------------------------
        # One item per processed image, keyed on the image identifier so
        # that writes are idempotent (design document ADR-005).
        metadata_table = dynamodb.Table(
            self,
            "MetadataTable",
            partition_key=dynamodb.Attribute(
                name="imageId", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # --- Queues --------------------------------------------------------
        # The dead-letter queue holds messages that fail repeatedly.
        dead_letter_queue = sqs.Queue(
            self, "DeadLetterQueue", retention_period=Duration.days(14)
        )
        # The work queue. The visibility timeout is six times the function
        # timeout (design document Section 8.2); the redrive policy moves a
        # message to the dead-letter queue after five failed receives.
        work_queue = sqs.Queue(
            self,
            "WorkQueue",
            visibility_timeout=Duration.seconds(720),
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=5, queue=dead_letter_queue
            ),
        )

        # --- Worker --------------------------------------------------------
        # The worker is a Lambda function packaged as a container image,
        # built from the Dockerfile at the repository root.
        #
        # The function and its image both use the arm64 architecture. This
        # matches an Apple Silicon build machine, so the image builds
        # natively without emulation, and arm64 (Graviton) Lambda is fully
        # supported and lower cost. The function architecture and the image
        # platform must agree, or Lambda cannot start the container.
        #
        # No reserved concurrency is set: this AWS account has a low Lambda
        # concurrency limit, so reserving capacity would leave too little in
        # the shared pool. The function scales within the account's limit
        # instead (design document Section 7.6).
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

        # The SQS event source mapping. A batch size of one means one image
        # per invocation (design document Section 7.2). This also grants the
        # worker permission to receive and delete messages from the queue.
        worker.add_event_source(
            event_sources.SqsEventSource(work_queue, batch_size=1)
        )

        # --- Permissions (least privilege) ---------------------------------
        input_bucket.grant_read(worker)
        output_bucket.grant_write(worker)
        metadata_table.grant_write_data(worker)

        # --- Outputs -------------------------------------------------------
        # The values the submitter needs in order to send work.
        cdk.CfnOutput(self, "InputBucketName", value=input_bucket.bucket_name)
        cdk.CfnOutput(self, "OutputBucketName", value=output_bucket.bucket_name)
        cdk.CfnOutput(self, "WorkQueueUrl", value=work_queue.queue_url)
        cdk.CfnOutput(self, "MetadataTableName", value=metadata_table.table_name)
