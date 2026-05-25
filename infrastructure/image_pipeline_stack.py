"""The AWS CDK stack: every resource the system uses.

Resources to define (design document Sections 4.2 and 11):
  - two S3 buckets: input and output
  - an SQS queue, with a second SQS queue as its dead-letter queue
  - a DynamoDB table for the metadata
  - the Lambda function (packaged as a container image from worker/)
  - the SQS event source mapping for the Lambda function
  - the IAM role for the Lambda function, with least-privilege permissions
  - CloudWatch log configuration

The stack should also pass the bucket and table names to the Lambda
function as environment variables (see shared/config.py).
"""
# TODO: implement using aws_cdk
