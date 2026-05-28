# Image Pipeline

A distributed, scalable, fault-tolerant image-processing pipeline on Amazon Web Services.
See the accompanying design document for the full architecture.

## Overview

The pipeline takes a directory of source images and processes each one into three WebP derivatives sized 256, 512, and 1024 pixels on the longest edge, with EXIF metadata stripped. Images are uploaded to an S3 input bucket and a message per image is placed on an SQS work queue. AWS Lambda picks the messages up, runs the worker in parallel, writes the derivatives to an S3 output bucket, and writes one metadata record per image to DynamoDB. The number of concurrent workers rises and falls with the queue automatically, so the system absorbs bursts and scales to zero when idle. Failed messages are retried through the queue's visibility timeout, and messages that cannot be processed are isolated in a dead-letter queue.

## Repository structure

- `worker/` the AWS Lambda function that processes one image
- `submitter/` the command-line tool that uploads images and enqueues work
- `infrastructure/` the AWS CDK application that defines all cloud resources
- `shared/` shared configuration and utilities
- `tests/` the automated test suite

## Prerequisites

- Python 3.11 or later
- An AWS account with configured credentials
- Docker, installed and running (the worker is built as a container image)
- The AWS CDK command-line tool (`npm install -g aws-cdk`)

## Setup

    python -m venv .venv
    source .venv/bin/activate
    pip install -e ".[dev,infra]"

## Running the tests

    pytest

## Deploying

The system is deployed to AWS with the AWS CDK. Docker must be running,
because the worker is built as a container image.

1. Configure your AWS credentials, for example with `aws configure`.
2. Bootstrap the AWS environment once per account and region:

       cdk bootstrap

3. Deploy the stack:

       cdk deploy

The deploy prints four outputs: the input bucket name, the output bucket
name, the work queue URL, and the metadata table name.

## Submitting images

Use the submitter, passing the input bucket name and work queue URL from the
deploy outputs:

    python submitter/submit.py path/to/images \
        --input-bucket <InputBucketName> \
        --queue-url <WorkQueueUrl>

## Tearing down

To remove all the resources and stop incurring cost:

    cdk destroy

## Author

Carmen Brits. Built as the assessment for the Distributed Cloud-Based Data-Processing System module.
