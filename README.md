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
- The AWS CDK command-line tool

## Setup

    python -m venv .venv
    source .venv/bin/activate
    pip install -e ".[dev,infra]"

## Running the tests

    pytest

## Deploying

<!-- TODO: complete this once the infrastructure is written. -->

## Author

<!-- TODO: your name and student ID. -->
