#!/usr/bin/env python3
"""Send a single test email using the configured SES transport."""

from __future__ import annotations

import argparse
import os

from dotenv import load_dotenv

from ses_warmup import build_config, get_ses_client, get_smtp_client, send_email


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send one test email with the current SES settings.")
    parser.add_argument("recipient", help="Destination email address")
    parser.add_argument(
        "--subject-file",
        default="data/email_templates/warmup_subject.txt",
        help="Path to subject template",
    )
    parser.add_argument(
        "--html-file",
        default="data/email_templates/warmup_body.html",
        help="Path to HTML template",
    )
    parser.add_argument(
        "--text-file",
        default="data/email_templates/warmup_body.txt",
        help="Path to plain-text template",
    )
    return parser.parse_args()


def main() -> int:
    load_dotenv()
    args = parse_args()

    fake_args = argparse.Namespace(
        from_email=os.getenv("SES_FROM_EMAIL"),
        from_name=os.getenv("SES_FROM_NAME"),
        reply_to=os.getenv("SES_REPLY_TO", ""),
        subject=None,
        subject_file=args.subject_file,
        html=None,
        html_file=args.html_file,
        text=None,
        text_file=args.text_file,
        region=os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-2",
        configuration_set=os.getenv("SES_CONFIGURATION_SET"),
        list_management_topic=os.getenv("SES_LIST_MANAGEMENT_TOPIC"),
        campaign_name=os.getenv("SES_CAMPAIGN_NAME", ""),
        stream_name=os.getenv("SES_STREAM_NAME", ""),
        email_tag=[],
        rate_per_second=None,
        transport=os.getenv("SES_TRANSPORT", "api"),
        smtp_host=os.getenv("SES_SMTP_HOST"),
        smtp_port=int(os.getenv("SES_SMTP_PORT", "587")),
        smtp_username=os.getenv("SES_SMTP_USERNAME"),
        smtp_password=os.getenv("SES_SMTP_PASSWORD"),
    )

    plan = {"default_rate_per_second": 1.0}
    config = build_config(fake_args, plan)
    client = get_smtp_client(config) if config.transport == "smtp" else get_ses_client(config.region)
    try:
        message_id = send_email(client, config, args.recipient)
    finally:
        if config.transport == "smtp":
            try:
                client.quit()
            except Exception:
                pass

    print(f"Sent test email to {args.recipient}")
    print(f"Transport: {config.transport}")
    print(f"MessageId: {message_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
