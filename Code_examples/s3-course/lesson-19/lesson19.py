from contextlib import closing
from pathlib import Path
import boto3
from boto3.s3.transfer import TransferConfig
from botocore.config import Config

BUCKET = "s3-course-lesson1"
KEY = "lesson19/big.bin"
MIB = 1024 * 1024

s3 = boto3.client(
    "s3",
    endpoint_url="http://127.0.0.1:9000",
    region_name="us-east-1",
    config=Config(
        signature_version="s3v4",
        s3={"addressing_style": "path"},
    ),
)

transfer = TransferConfig(
    multipart_threshold=8 * MIB,
    multipart_chunksize=8 * MIB,
    max_concurrency=2,
)

s3.upload_file("big.bin", BUCKET, KEY, Config=transfer)
print("Uploaded:", s3.head_object(Bucket=BUCKET, Key=KEY)["ContentLength"])

response = s3.get_object(Bucket=BUCKET, Key=KEY)
with closing(response["Body"]) as source, open("copy.bin", "wb") as target:
    while chunk := source.read(MIB):
        target.write(chunk)

print("Downloaded:", Path("copy.bin").stat().st_size)
