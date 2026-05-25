"""Command-line submitter.

Uploads a directory of source images to the input S3 bucket and places one
SQS message per image. See design document Section 5.3.
"""


def main() -> None:
    """Entry point for the submitter.

    Steps to implement:
      1. Parse command-line arguments: the input directory, and optionally
         a job identifier (use argparse).
      2. For each image file in the directory:
         - generate an image identifier;
         - upload the file to the input S3 bucket;
         - send one SQS message with imageId, inputKey, jobId, submittedAt.
      3. Print a short summary, for example how many images were submitted.
    """
    # TODO: implement using boto3 and argparse
    raise NotImplementedError


if __name__ == "__main__":
    main()
