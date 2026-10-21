import boto3
from botocore.config import Config

session = boto3.Session(profile_name="lesson12-reader")
s3 = session.client(
    "s3", endpoint_url="http://127.0.0.1:9000",
    region_name="us-east-1",
    config=Config(signature_version="s3v4",
                  s3={"addressing_style": "path"}),
)
for operation in ("put_object", "get_object"):
    print(s3.generate_presigned_url(
        operation,
        Params={"Bucket": "s3-course-lesson1", "Key": "lesson14/upload.txt"},
        ExpiresIn=300,
    ))
