from pathlib import Path
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

BUCKET = "s3-course-lesson1"
KEY = "lesson18/hello.txt"

s3 = boto3.client(
    "s3",
    endpoint_url="http://127.0.0.1:9000",
    region_name="us-east-1",
    config=Config(
        signature_version="s3v4",
        s3={"addressing_style": "path"},
    ),
)

try:
    s3.create_bucket(Bucket=BUCKET)
    print("Bucket created")
except ClientError as e:
    code = e.response["Error"]["Code"]
    if code in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
        print("Bucket already exists")
    else:
        raise

Path("hello.txt").write_bytes(b"hello from boto3\n")
s3.upload_file("hello.txt", BUCKET, KEY)

info = s3.head_object(Bucket=BUCKET, Key=KEY)
print("Size:", info["ContentLength"])

s3.download_file(BUCKET, KEY, "downloaded.txt")
assert Path("hello.txt").read_bytes() == Path("downloaded.txt").read_bytes()
print("OK: downloaded bytes match")
