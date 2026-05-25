# Image Pipeline

A distributed, scalable, fault-tolerant image-processing pipeline on Amazon Web Services.
See the accompanying design document for the full architecture.

## Overview

<!-- TODO: a short paragraph, in your own words, describing what the system does. -->

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

<!-- TODO: your name and student ID. -->
