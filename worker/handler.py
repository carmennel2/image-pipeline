"""Lambda entry point and orchestration for the worker.

Receives an SQS event and coordinates the other components to process one
image. See Section 5.1 of the design document.
"""


def handler(event, context):
    """AWS Lambda entry point.

    Steps to implement:
      1. Read the SQS record from `event` (batch size is 1, so expect one).
      2. Parse the message body: imageId, inputKey, jobId.
      3. Call the downloader to fetch the source image from S3.
      4. Call the processor to produce the derivatives.
      5. Call the uploader to store the derivatives in the output bucket.
      6. Call the metadata writer to record the result in DynamoDB.
      7. Return normally on success so Lambda deletes the message.

    Wrap the work with the error handler (see errors.py) so transient
    failures are retried and permanent failures are handled correctly.
    """
    # TODO: implement
    raise NotImplementedError
