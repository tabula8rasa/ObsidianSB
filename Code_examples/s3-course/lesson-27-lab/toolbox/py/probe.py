#!/usr/bin/env python3
"""probe — один «замер» кластера для опыта с quorum. Печатает JSON.

  probe.py --cluster a --entry a2-n1 --bucket lab --get KEY --put-count 60 --prefix quorum/k3/
Делает: 1) GET существующего объекта KEY (читаем целиком);  2) N новых PUT.
Ошибки не скрывает: код ошибки S3 попадает в сводку.
"""
import argparse
import json
import os
import sys
import time

import botocore.session
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cluster", required=True)
    ap.add_argument("--entry", required=True)
    ap.add_argument("--bucket", required=True)
    ap.add_argument("--get")
    ap.add_argument("--expect-size", type=int)
    ap.add_argument("--put-count", type=int, default=0)
    ap.add_argument("--put-size", type=int, default=262144)
    ap.add_argument("--prefix", default="probe/")
    a = ap.parse_args()

    up = a.cluster.upper()
    s3 = botocore.session.get_session().create_client(
        "s3",
        endpoint_url=f"http://{a.entry}:9000",
        region_name="us-east-1",
        aws_access_key_id=os.environ[f"{up}_ACCESS_KEY"],
        aws_secret_access_key=os.environ[f"{up}_SECRET_KEY"],
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
            connect_timeout=3,
            read_timeout=20,
            retries={"max_attempts": 1},
        ),
    )

    def err(e):
        if isinstance(e, ClientError):
            return e.response.get("Error", {}).get("Code") or "ClientError"
        return type(e).__name__

    out = {"entry": a.entry}

    if a.get:
        t = time.time()
        try:
            body = s3.get_object(Bucket=a.bucket, Key=a.get)["Body"].read()
            ok = a.expect_size is None or len(body) == a.expect_size
            out["get"] = {"ok": ok, "bytes": len(body), "error": None if ok else "SizeMismatch"}
        except (ClientError, BotoCoreError) as e:
            out["get"] = {"ok": False, "bytes": 0, "error": err(e)}
        out["get"]["ms"] = int((time.time() - t) * 1000)

    if a.put_count:
        payload = os.urandom(a.put_size)
        ok_keys, errors = [], {}
        for i in range(a.put_count):
            key = f"{a.prefix}{i:03d}.bin"
            try:
                s3.put_object(Bucket=a.bucket, Key=key, Body=payload)
                ok_keys.append(key)
            except (ClientError, BotoCoreError) as e:
                errors[err(e)] = errors.get(err(e), 0) + 1
        out["put"] = {"ok": len(ok_keys), "fail": a.put_count - len(ok_keys), "errors": errors}

    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"fatal": f"{type(e).__name__}: {e}"}))
        sys.exit(1)
