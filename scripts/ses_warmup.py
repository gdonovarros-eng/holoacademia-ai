#!/usr/bin/env python3
"""Run a gradual Amazon SES warm-up campaign from CSV contact lists."""

from __future__ import annotations

import argparse
import csv
import json
import os
import smtplib
import ssl
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


DEFAULT_PLAN_FILE = Path("data/ses_warmup_plan.json")
DEFAULT_STATE_FILE = Path("data/ses_warmup_state.json")
DEFAULT_LOG_FILE = Path("data/ses_warmup_runs.jsonl")
DEFAULT_FAILURE_FILE = Path("data/ses_warmup_failures.csv")
DEFAULT_SUPPRESSION_FILE = Path("data/ses_suppression.csv")


@dataclass
class WarmupConfig:
    transport: str
    from_email: str
    from_name: str | None
    subject: str
    html_body: str | None
    text_body: str | None
    region: str
    reply_to: list[str]
    configuration_set: str | None
    list_management_topic: str | None
    email_tags: list[dict[str, str]]
    rate_per_second: float
    smtp_host: str | None
    smtp_port: int
    smtp_username: str | None
    smtp_password: str | None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Envio gradual con Amazon SES para calentamiento de dominio/IP."
    )
    parser.add_argument(
        "--list-dir",
        required=True,
        help="Carpeta con los CSV numerados, por ejemplo 1.csv, 2.csv y 3.csv",
    )
    parser.add_argument(
        "--state-file",
        default=str(DEFAULT_STATE_FILE),
        help="Archivo JSON donde se guarda el avance entre ejecuciones",
    )
    parser.add_argument(
        "--log-file",
        default=str(DEFAULT_LOG_FILE),
        help="Archivo JSONL con el resumen de cada corrida",
    )
    parser.add_argument(
        "--failure-file",
        default=str(DEFAULT_FAILURE_FILE),
        help="Archivo CSV donde se registran los envios fallidos",
    )
    parser.add_argument(
        "--suppression-file",
        default=str(DEFAULT_SUPPRESSION_FILE),
        help="CSV opcional con una columna email para excluir rebotes/quejas/bajas",
    )
    parser.add_argument(
        "--plan-file",
        default=str(DEFAULT_PLAN_FILE),
        help="JSON con el plan de warm-up diario",
    )
    parser.add_argument(
        "--from-email",
        default=None,
        help="Remitente verificado en SES. Default: env SES_FROM_EMAIL",
    )
    parser.add_argument(
        "--from-name",
        default=None,
        help="Nombre visible del remitente. Default: env SES_FROM_NAME",
    )
    parser.add_argument(
        "--transport",
        choices=("api", "smtp"),
        default=None,
        help="Canal de envio: api o smtp. Default: env SES_TRANSPORT o smtp",
    )
    parser.add_argument(
        "--reply-to",
        default="",
        help="Uno o varios reply-to separados por coma",
    )
    parser.add_argument(
        "--subject-file",
        help="Archivo de texto con el asunto del correo",
    )
    parser.add_argument(
        "--html-file",
        help="Archivo HTML del mensaje",
    )
    parser.add_argument(
        "--text-file",
        help="Archivo TXT del mensaje",
    )
    parser.add_argument(
        "--subject",
        help="Asunto directo si no quieres usar --subject-file",
    )
    parser.add_argument(
        "--html",
        help="HTML directo si no quieres usar --html-file",
    )
    parser.add_argument(
        "--text",
        help="Texto directo si no quieres usar --text-file",
    )
    parser.add_argument(
        "--region",
        default=None,
        help="Region AWS para SES. Default: env AWS_REGION o us-east-1",
    )
    parser.add_argument(
        "--smtp-host",
        default=None,
        help="Host SMTP de SES, por ejemplo email-smtp.us-east-1.amazonaws.com",
    )
    parser.add_argument(
        "--smtp-port",
        type=int,
        default=None,
        help="Puerto SMTP de SES. Default: env SES_SMTP_PORT o 587",
    )
    parser.add_argument(
        "--smtp-username",
        default=None,
        help="Usuario SMTP de SES",
    )
    parser.add_argument(
        "--smtp-password",
        default=None,
        help="Password SMTP de SES",
    )
    parser.add_argument(
        "--configuration-set",
        default=None,
        help="Configuration set de SES para tracking",
    )
    parser.add_argument(
        "--list-management-topic",
        default=None,
        help="Topic de contact list para unsubscribe si ya lo usas en SES",
    )
    parser.add_argument(
        "--campaign-name",
        default="",
        help="Nombre corto de la campana para tagging y metricas",
    )
    parser.add_argument(
        "--stream-name",
        default="",
        help="Nombre del carril de envio, por ejemplo warmup o announcement",
    )
    parser.add_argument(
        "--email-tag",
        action="append",
        default=[],
        help="Tag extra para SES en formato clave=valor. Se puede repetir.",
    )
    parser.add_argument(
        "--rate-per-second",
        type=float,
        help="Ritmo maximo por segundo. Si no se indica, toma el del plan",
    )
    parser.add_argument(
        "--max-send",
        type=int,
        help="Sobrescribe el tope del dia actual",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Envia de verdad. Sin este flag solo hace dry-run",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Permite correr mas de una vez el mismo dia",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=0.0,
        help="Pausa fija adicional entre envios",
    )
    parser.add_argument(
        "--preview-count",
        type=int,
        default=25,
        help="Cuantos destinatarios mostrar en dry-run",
    )
    parser.add_argument(
        "--priority-emails",
        default="",
        help="Correos a mover al inicio de la parte no enviada. Acepta coma o punto y coma.",
    )
    return parser.parse_args()


def read_text_arg(direct_value: str | None, file_path: str | None) -> str | None:
    if direct_value is not None:
        return apply_template_vars(direct_value)
    if file_path:
        return apply_template_vars(Path(file_path).read_text(encoding="utf-8").strip())
    return None


def apply_template_vars(text: str) -> str:
    replacements = {
        "{{UNSUBSCRIBE_URL}}": os.getenv("EMAIL_UNSUBSCRIBE_URL", "#"),
        "{{SUPPORT_EMAIL}}": os.getenv("EMAIL_SUPPORT_EMAIL", os.getenv("SES_REPLY_TO", "")),
        "{{FROM_EMAIL}}": os.getenv("SES_FROM_EMAIL", ""),
        "{{BRAND_NAME}}": os.getenv("EMAIL_BRAND_NAME", "Holoacademia"),
    }
    for placeholder, value in replacements.items():
        text = text.replace(placeholder, value)
    return text


def parse_email_tags(raw_tags: list[str], campaign_name: str, stream_name: str) -> list[dict[str, str]]:
    tags: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def add_tag(name: str, value: str) -> None:
        cleaned_name = name.strip()
        cleaned_value = value.strip()
        if not cleaned_name or not cleaned_value:
            return
        pair = (cleaned_name, cleaned_value)
        if pair in seen:
            return
        seen.add(pair)
        tags.append({"Name": cleaned_name, "Value": cleaned_value})

    if campaign_name.strip():
        add_tag("campaign", campaign_name)
    if stream_name.strip():
        add_tag("stream", stream_name)

    for raw in raw_tags:
        if "=" not in raw:
            raise ValueError(f"Tag invalido '{raw}'. Usa clave=valor.")
        name, value = raw.split("=", 1)
        add_tag(name, value)

    return tags


def load_plan(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"No existe el plan de warm-up: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def parse_iso_date(raw: str | None) -> date | None:
    if not raw:
        return None
    return date.fromisoformat(raw)


def list_csv_files(list_dir: Path) -> list[Path]:
    files = sorted(
        [path for path in list_dir.iterdir() if path.is_file() and path.suffix.lower() == ".csv"],
        key=sort_key,
    )
    if not files:
        raise ValueError(f"No encontre CSV en {list_dir}")
    return files


def sort_key(path: Path) -> tuple[int, str]:
    stem = path.stem
    if stem.isdigit():
        return (0, f"{int(stem):09d}")
    return (1, stem.lower())


def load_audience(list_dir: Path, suppression_file: Path) -> tuple[list[str], set[str]]:
    audience: list[str] = []
    seen: set[str] = set()
    suppression = load_suppression(suppression_file)

    for csv_path in list_csv_files(list_dir):
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or "email" not in {name.strip().lower() for name in reader.fieldnames}:
                raise ValueError(f"El archivo {csv_path} no tiene una columna 'email'")
            for row in reader:
                raw_email = row.get("email") or row.get("Email") or ""
                email = raw_email.strip().lower()
                if not email or email in seen or email in suppression:
                    continue
                seen.add(email)
                audience.append(email)

    if not audience:
        raise ValueError("La audiencia final quedo vacia.")
    return audience, suppression


def load_suppression(path: Path) -> set[str]:
    if not path.exists():
        return set()

    suppression: set[str] = set()
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            return suppression
        field_map = {field.strip().lower(): field for field in reader.fieldnames}
        email_field = field_map.get("email")
        if not email_field:
            return suppression
        for row in reader:
            email = (row.get(email_field) or "").strip().lower()
            if email:
                suppression.add(email)
    return suppression


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "cursor": 0,
            "total_sent": 0,
            "run_count": 0,
            "history": [],
        }
    return json.loads(path.read_text(encoding="utf-8"))


def parse_priority_emails(raw: str) -> list[str]:
    normalized = raw.replace(";", ",").replace("\n", ",")
    emails: list[str] = []
    seen: set[str] = set()
    for part in normalized.split(","):
        email = part.strip().lower()
        if email and email not in seen:
            seen.add(email)
            emails.append(email)
    return emails


def prioritize_remaining_audience(
    audience: list[str], cursor: int, priority_emails: list[str]
) -> tuple[list[str], list[str]]:
    if not priority_emails or cursor >= len(audience):
        return audience, []

    sent_slice = audience[:cursor]
    remaining = audience[cursor:]
    remaining_set = set(remaining)
    matched = [email for email in priority_emails if email in remaining_set]
    if not matched:
        return audience, []

    matched_set = set(matched)
    reordered = sent_slice + matched + [email for email in remaining if email not in matched_set]
    return reordered, matched


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=True, indent=2), encoding="utf-8")


def append_run_log(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=True) + "\n")


def append_failure(path: Path, email: str, error_code: str, error_message: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists()
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        if write_header:
            writer.writerow(["timestamp_utc", "email", "error_code", "error_message"])
        writer.writerow([utc_now_iso(), email, error_code, error_message])


def utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def is_transient_send_error(exc: Exception) -> bool:
    error_code = getattr(exc, "response", {}).get("Error", {}).get("Code", "")
    transient_codes = {
        "EndpointConnectionError",
        "RequestTimeout",
        "Throttling",
        "TooManyRequestsException",
        "ServiceUnavailable",
        "ServiceUnavailableException",
    }
    if error_code in transient_codes:
        return True

    transient_names = {
        "EndpointConnectionError",
        "ConnectTimeoutError",
        "ReadTimeoutError",
        "ConnectionError",
        "TimeoutError",
        "SMTPServerDisconnected",
    }
    if exc.__class__.__name__ in transient_names:
        return True

    message = str(exc).lower()
    return any(
        snippet in message
        for snippet in (
            "could not connect to the endpoint url",
            "connection was closed",
            "timed out",
            "temporarily unavailable",
            "connection reset",
        )
    )


def determine_limit_for_run(plan: dict[str, Any], run_number: int) -> int:
    limits = plan.get("daily_limits") or []
    if not limits:
        raise ValueError("El plan no trae daily_limits")
    if run_number <= len(limits):
        return int(limits[run_number - 1])
    if plan.get("pause_after_plan"):
        raise ValueError(
            plan.get("pause_message")
            or "El plan llego al final y esta en pausa hasta que autorices una nueva escala."
        )
    return int(limits[-1])


def determine_due_runs(plan: dict[str, Any], last_run_date: str | None, today: str) -> int:
    if not plan.get("catch_up_missed_days", True):
        return 1
    last_date = parse_iso_date(last_run_date)
    today_date = parse_iso_date(today)
    if today_date is None:
        raise ValueError("La fecha actual no es valida.")
    if last_date is None:
        return 1
    delta_days = (today_date - last_date).days
    if delta_days <= 0:
        return 1
    return delta_days


def determine_combined_limit(
    plan: dict[str, Any], start_run_number: int, due_runs: int, override: int | None
) -> tuple[int, list[int]]:
    if override is not None:
        return override, [override]

    limits: list[int] = []
    for offset in range(due_runs):
        limits.append(determine_limit_for_run(plan, start_run_number + offset))
    return sum(limits), limits


def get_pending_run(state: dict[str, Any], today: str) -> dict[str, Any] | None:
    pending = state.get("pending_run")
    if not isinstance(pending, dict):
        return None
    if pending.get("date") != today:
        return None
    target_limit = int(pending.get("target_limit", 0))
    processed = int(pending.get("processed", 0))
    if target_limit <= 0 or processed >= target_limit:
        return None
    return pending


def build_config(args: argparse.Namespace, plan: dict[str, Any]) -> WarmupConfig:
    subject = read_text_arg(args.subject, args.subject_file)
    html_body = read_text_arg(args.html, args.html_file)
    text_body = read_text_arg(args.text, args.text_file)
    from_email = args.from_email or os.getenv("SES_FROM_EMAIL")
    from_name = args.from_name or os.getenv("SES_FROM_NAME")
    region = args.region or os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"
    configuration_set = args.configuration_set or os.getenv("SES_CONFIGURATION_SET")
    list_management_topic = args.list_management_topic or os.getenv("SES_LIST_MANAGEMENT_TOPIC")
    smtp_host = args.smtp_host or os.getenv("SES_SMTP_HOST")
    smtp_port = args.smtp_port or int(os.getenv("SES_SMTP_PORT", "587"))
    smtp_username = args.smtp_username or os.getenv("SES_SMTP_USERNAME")
    smtp_password = args.smtp_password or os.getenv("SES_SMTP_PASSWORD")
    transport = args.transport or os.getenv("SES_TRANSPORT", "smtp")
    reply_to_raw = args.reply_to if args.reply_to else os.getenv("SES_REPLY_TO", "")

    if not from_email:
        raise ValueError("Falta --from-email o la variable SES_FROM_EMAIL")
    if not subject:
        raise ValueError("Falta el asunto: usa --subject o --subject-file")
    if not html_body and not text_body:
        raise ValueError("Necesitas --html/--html-file o --text/--text-file")
    if transport == "smtp":
        if not smtp_host:
            raise ValueError("Falta --smtp-host o la variable SES_SMTP_HOST")
        if not smtp_username:
            raise ValueError("Falta --smtp-username o la variable SES_SMTP_USERNAME")
        if not smtp_password:
            raise ValueError("Falta --smtp-password o la variable SES_SMTP_PASSWORD")

    reply_to = [item.strip() for item in reply_to_raw.split(",") if item.strip()]
    email_tags = parse_email_tags(args.email_tag, args.campaign_name, args.stream_name)
    rate_per_second = args.rate_per_second or float(plan.get("default_rate_per_second", 1.0))

    return WarmupConfig(
        transport=transport,
        from_email=from_email,
        from_name=from_name,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
        region=region,
        reply_to=reply_to,
        configuration_set=configuration_set,
        list_management_topic=list_management_topic,
        email_tags=email_tags,
        rate_per_second=rate_per_second,
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_username=smtp_username,
        smtp_password=smtp_password,
    )


def get_ses_client(region: str):
    try:
        import boto3
    except ImportError as exc:
        raise RuntimeError("Falta boto3. Instala dependencias con pip install -r requirements.txt") from exc

    return boto3.client("sesv2", region_name=region)


def get_smtp_client(config: WarmupConfig):
    client = smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=30)
    client.ehlo()
    if config.smtp_port in (587, 2587):
        client.starttls(context=ssl.create_default_context())
        client.ehlo()
    client.login(config.smtp_username, config.smtp_password)
    return client


def send_email(client, config: WarmupConfig, recipient: str) -> str:
    from_header = formataddr((config.from_name, config.from_email)) if config.from_name else config.from_email

    if config.transport == "smtp":
        message = EmailMessage()
        message["Subject"] = config.subject
        message["From"] = from_header
        message["To"] = recipient
        if config.reply_to:
            message["Reply-To"] = ", ".join(config.reply_to)
        if config.configuration_set:
            message["X-SES-CONFIGURATION-SET"] = config.configuration_set
        for tag in config.email_tags:
            message[f"X-SES-MESSAGE-TAGS"] = f"{tag['Name']}={tag['Value']}"
        if config.text_body and config.html_body:
            message.set_content(config.text_body)
            message.add_alternative(config.html_body, subtype="html")
        elif config.html_body:
            message.add_alternative(config.html_body, subtype="html")
        else:
            message.set_content(config.text_body or "")

        client.send_message(message)
        return f"smtp-{utc_now_iso()}-{recipient}"

    content: dict[str, Any] = {
        "Simple": {
            "Subject": {"Data": config.subject, "Charset": "UTF-8"},
            "Body": {},
        }
    }
    if config.html_body:
        content["Simple"]["Body"]["Html"] = {"Data": config.html_body, "Charset": "UTF-8"}
    if config.text_body:
        content["Simple"]["Body"]["Text"] = {"Data": config.text_body, "Charset": "UTF-8"}

    payload: dict[str, Any] = {
        "FromEmailAddress": from_header,
        "Destination": {"ToAddresses": [recipient]},
        "Content": content,
    }
    if config.configuration_set:
        payload["ConfigurationSetName"] = config.configuration_set
    if config.email_tags:
        payload["EmailTags"] = config.email_tags
    if config.reply_to:
        payload["ReplyToAddresses"] = config.reply_to
    if config.list_management_topic:
        payload["ListManagementOptions"] = {"TopicName": config.list_management_topic}

    response = client.send_email(**payload)
    return response["MessageId"]


def run(args: argparse.Namespace) -> int:
    load_dotenv()

    plan = load_plan(Path(args.plan_file))
    config = build_config(args, plan)
    list_dir = Path(args.list_dir)
    state_path = Path(args.state_file)
    log_path = Path(args.log_file)
    failure_path = Path(args.failure_file)
    suppression_path = Path(args.suppression_file)

    audience, suppression = load_audience(list_dir, suppression_path)
    state = load_state(state_path)
    today = datetime.now().date().isoformat()

    last_run_date = state.get("last_run_date")
    if last_run_date == today and not args.force:
        print(f"Hoy ({today}) ya hubo una corrida. Usa --force si de verdad quieres repetirla.")
        return 0

    cursor = int(state.get("cursor", 0))
    if cursor >= len(audience):
        print("La lista completa ya fue recorrida.")
        return 0

    priority_emails = parse_priority_emails(args.priority_emails)
    audience, prioritized_matches = prioritize_remaining_audience(audience, cursor, priority_emails)

    pending_run = get_pending_run(state, today) if args.max_send is None else None
    if pending_run:
        start_run_number = int(pending_run.get("run_span_start", pending_run.get("run_number", 1)))
        run_number = int(pending_run.get("run_number", start_run_number))
        due_runs = int(pending_run.get("days_caught_up", 1))
        combined_limits = [int(value) for value in pending_run.get("combined_limits", [pending_run["target_limit"]])]
        target_limit = int(pending_run["target_limit"])
        already_processed = int(pending_run.get("processed", 0))
    else:
        start_run_number = int(state.get("run_count", 0)) + 1
        due_runs = determine_due_runs(plan, last_run_date, today)
        target_limit, combined_limits = determine_combined_limit(plan, start_run_number, due_runs, args.max_send)
        run_number = start_run_number + due_runs - 1
        already_processed = 0
    remaining = len(audience) - cursor
    remaining_target = max(target_limit - already_processed, 0)
    send_limit = min(remaining_target, remaining)

    if due_runs == 1:
        print(f"Run #{run_number}")
    else:
        print(f"Runs acumulados #{start_run_number}-#{run_number}")
    print(f"Audiencia total: {len(audience)}")
    print(f"Excluidos por suppression: {len(suppression)}")
    print(f"Cursor actual: {cursor}")
    print(f"Objetivo de envio hoy: {send_limit}")
    if already_processed:
        print(f"Ya procesados hoy en esta corrida parcial: {already_processed}")
    if args.max_send is None and due_runs > 1:
        print(f"Limites combinados por atraso: {combined_limits}")
    print(f"Modo: {'EXECUTE' if args.execute else 'DRY-RUN'}")
    if config.configuration_set:
        print(f"Configuration set: {config.configuration_set}")
    if config.email_tags:
        print(f"Tags SES: {config.email_tags}")
    if prioritized_matches:
        print("Prioridad incluida al inicio de la tanda:")
        for email in prioritized_matches:
            print(f"- {email}")

    message_ids: list[str] = []
    sent_count = 0
    failed_count = 0
    processed_count = already_processed
    started_at = utc_now_iso()
    initial_total_sent = int(state.get("total_sent", 0))

    if args.execute and not pending_run:
        state["pending_run"] = {
            "date": today,
            "run_number": run_number,
            "run_span_start": start_run_number,
            "run_span_end": run_number,
            "days_caught_up": due_runs,
            "target_limit": target_limit,
            "combined_limits": combined_limits,
            "processed": already_processed,
        }
        save_state(state_path, state)

    client = None
    if args.execute:
        client = get_smtp_client(config) if config.transport == "smtp" else get_ses_client(config.region)

    preview_cursor = cursor
    batch = audience[cursor : cursor + send_limit]
    try:
        for email in batch:
            if args.execute:
                try:
                    message_id = send_email(client, config, email)
                    message_ids.append(message_id)
                    sent_count += 1
                    processed_count += 1
                    state["total_sent"] = initial_total_sent + sent_count
                    cursor += 1
                    state["cursor"] = cursor
                    if args.execute:
                        state["pending_run"]["processed"] = processed_count
                    save_state(state_path, state)
                except Exception as exc:
                    if is_transient_send_error(exc):
                        print(f"Error transitorio al enviar a {email}: {exc}", file=sys.stderr)
                        print("Se detiene la corrida para reintentar el mismo correo despues.", file=sys.stderr)
                        raise
                    failed_count += 1
                    processed_count += 1
                    error_code = getattr(exc, "response", {}).get("Error", {}).get("Code", exc.__class__.__name__)
                    error_message = getattr(exc, "response", {}).get("Error", {}).get("Message", str(exc))
                    append_failure(failure_path, email, error_code, error_message)
                    cursor += 1
                    state["cursor"] = cursor
                    if args.execute:
                        state["pending_run"]["processed"] = processed_count
                    save_state(state_path, state)
            else:
                if sent_count < max(args.preview_count, 0):
                    print(email)
                sent_count += 1
                preview_cursor += 1

            if args.execute and config.rate_per_second > 0:
                time.sleep((1.0 / config.rate_per_second) + max(args.sleep_seconds, 0.0))
    finally:
        if client is not None and config.transport == "smtp":
            try:
                client.quit()
            except Exception:
                pass

    final_cursor = cursor if args.execute else preview_cursor
    state["cursor"] = cursor if args.execute else int(state.get("cursor", 0))
    state["total_sent"] = initial_total_sent + sent_count if args.execute else initial_total_sent
    history_entry = {
        "run_number": run_number,
        "run_span_start": start_run_number,
        "run_span_end": run_number,
        "days_caught_up": due_runs,
        "date": today,
        "started_at_utc": started_at,
        "finished_at_utc": utc_now_iso(),
        "target_limit": target_limit,
        "combined_limits": combined_limits,
        "attempted": send_limit,
        "sent": sent_count,
        "failed": failed_count,
        "cursor_after_run": final_cursor,
        "mode": "execute" if args.execute else "dry-run",
    }
    if args.execute:
        if processed_count >= target_limit:
            state["run_count"] = run_number
            state["last_run_date"] = today
            state.pop("pending_run", None)
            state.setdefault("history", []).append(history_entry)
        save_state(state_path, state)
    append_run_log(log_path, history_entry)

    print(f"Enviados: {sent_count}")
    print(f"Fallidos: {failed_count}")
    print(f"Cursor final: {final_cursor}/{len(audience)}")
    if not args.execute and send_limit > max(args.preview_count, 0):
        hidden = send_limit - max(args.preview_count, 0)
        print(f"Dry-run omitio {hidden} destinatarios adicionales del preview.")
    if message_ids:
        print(f"Ultimo MessageId: {message_ids[-1]}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(run(parse_args()))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
