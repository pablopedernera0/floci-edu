from flask import Flask, jsonify, render_template
import boto3
from botocore.client import Config
import os

app = Flask(__name__)

# ── Config desde variables de entorno ─────────────────────────────────────────
FLOCI_ENDPOINT  = os.getenv("FLOCI_ENDPOINT",  "http://localhost:4566")
FLOCI_REGION    = os.getenv("FLOCI_REGION",    "us-east-1")
FLOCI_ACCESS_KEY = os.getenv("FLOCI_ACCESS_KEY", "test")
FLOCI_SECRET_KEY = os.getenv("FLOCI_SECRET_KEY", "test")

def get_s3():
    return boto3.client(
        "s3",
        endpoint_url=FLOCI_ENDPOINT,
        region_name=FLOCI_REGION,
        aws_access_key_id=FLOCI_ACCESS_KEY,
        aws_secret_access_key=FLOCI_SECRET_KEY,
        config=Config(signature_version="s3v4"),
    )

def get_iam():
    return boto3.client(
        "iam",
        endpoint_url=FLOCI_ENDPOINT,
        region_name=FLOCI_REGION,
        aws_access_key_id=FLOCI_ACCESS_KEY,
        aws_secret_access_key=FLOCI_SECRET_KEY,
    )

# ── UI ────────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html",
                           endpoint=FLOCI_ENDPOINT,
                           region=FLOCI_REGION)

# ── API S3 ────────────────────────────────────────────────────────────────────
@app.route("/api/buckets")
def list_buckets():
    try:
        s3 = get_s3()
        resp = s3.list_buckets()
        buckets = [
            {"name": b["Name"], "created": b["CreationDate"].isoformat()}
            for b in resp.get("Buckets", [])
        ]
        return jsonify({"buckets": buckets})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/buckets/<bucket>/objects")
def list_objects(bucket):
    try:
        s3 = get_s3()
        resp = s3.list_objects_v2(Bucket=bucket)
        objects = []
        for obj in resp.get("Contents", []):
            objects.append({
                "key":          obj["Key"],
                "size":         obj["Size"],
                "last_modified": obj["LastModified"].isoformat(),
                "etag":         obj.get("ETag", "").strip('"'),
            })
        return jsonify({"objects": objects, "count": len(objects)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/buckets/<bucket>/objects/<path:key>/url")
def presign_object(bucket, key):
    try:
        s3 = get_s3()
        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=300,
        )
        return jsonify({"url": url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── API IAM ───────────────────────────────────────────────────────────────────
@app.route("/api/iam/users")
def list_iam_users():
    try:
        iam = get_iam()
        resp = iam.list_users()
        users = [
            {
                "username":   u["UserName"],
                "user_id":    u["UserId"],
                "arn":        u["Arn"],
                "created":    u["CreateDate"].isoformat(),
            }
            for u in resp.get("Users", [])
        ]
        return jsonify({"users": users})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=False)
