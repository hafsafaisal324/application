#!/usr/bin/env python3
import os
import json
import hmac
import hashlib
import datetime
import urllib.request

SUBMISSION_URL = "https://b12.io/apply/submission"

SIGNING_SECRET = b"hello-there-from-b12"  # treat like a secret in implementation

def iso8601_utc_now():
    # Example format they want: 2026-01-06T16:59:37.571Z
    now = datetime.datetime.now(datetime.timezone.utc)
    # keep milliseconds, always Z
    return now.isoformat(timespec="milliseconds").replace("+00:00", "Z")

def canonical_json_bytes(payload: dict) -> bytes:
    # keys sorted alphabetically, compact separators, UTF-8, no extra whitespace
    s = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return s.encode("utf-8")

def hmac_sha256_hex(data: bytes, key: bytes) -> str:
    return hmac.new(key, data, hashlib.sha256).hexdigest()

def github_action_run_link() -> str:
    # Build a link like: https://github.com/<owner>/<repo>/actions/runs/<run_id>
    server_url = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    run_id = os.environ.get("GITHUB_RUN_ID", "").strip()
    if repo and run_id:
        return f"{server_url}/{repo}/actions/runs/{run_id}"
    # Fallback if not running in Actions:
    return "https://github.com/<owner>/<repo>/actions/runs/<run_id>"

def main():
    name = os.environ.get("B12_NAME", "YOUR_NAME")
    email = os.environ.get("B12_EMAIL", "YOUR_EMAIL")
    resume_link = os.environ.get("B12_RESUME_LINK", "RESUME_LINK")  # PDF/LinkedIn/etc.

    # Repo link: use GitHub envs if available
    server_url = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    repository_link = os.environ.get("B12_REPOSITORY_LINK") or (f"{server_url}/{repo}" if repo else "https://github.com/<owner>/<repo>")

    action_run_link = github_action_run_link()

    payload = {
        "timestamp": iso8601_utc_now(),
        "name": name,
        "email": email,
        "resume_link": resume_link,
        "repository_link": repository_link,
        "action_run_link": action_run_link,
    }

    body = canonical_json_bytes(payload)
    digest = hmac_sha256_hex(body, SIGNING_SECRET)
    signature_header = f"sha256={digest}"

    req = urllib.request.Request(
        SUBMISSION_URL,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "X-Signature-256": signature_header,
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp_body = resp.read().decode("utf-8")
            # Expect: {"success": true, "receipt": "..."}
            data = json.loads(resp_body)
            receipt = data.get("receipt")
            if not receipt:
                raise RuntimeError(f"No receipt in response: {resp_body}")
            print(receipt)  # IMPORTANT: this is what they want you to copy/paste
    except Exception as e:
        raise SystemExit(f"Submission failed: {e}")

if __name__ == "__main__":
    main()
