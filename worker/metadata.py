"""Metadata Writer: records one item per processed image in DynamoDB."""


def write_record(table: str, record: dict) -> None:
    """Write the metadata record for one image to the DynamoDB `table`.

    The record MUST be keyed on the image identifier and written with
    put_item, which overwrites by key, so a repeated run replaces rather
    than duplicates the record (design document Section 8.3).
    """
    # TODO: implement using boto3
    raise NotImplementedError
