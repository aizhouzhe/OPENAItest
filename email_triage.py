#!/usr/bin/env python3
"""Daily email triage: find unread or unreplied messages via IMAP."""
from __future__ import annotations

import argparse
import json
import logging
import os
from datetime import datetime
from email import message_from_bytes
from email.header import decode_header, make_header
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import imaplib


LOGGER = logging.getLogger(__name__)


class ConfigError(RuntimeError):
    """Raised when configuration is invalid."""


def _load_config(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _get_config_value(config: Dict[str, Any], key: str, fallback: Optional[str] = None) -> str:
    value = config.get(key, os.environ.get(key.upper()))
    if value is None:
        if fallback is not None:
            return fallback
        raise ConfigError(f"Missing required config value: {key}")
    return value


def _decode_header(value: str) -> str:
    if not value:
        return "(no subject)"
    decoded = decode_header(value)
    return str(make_header(decoded))


def _imap_search(connection: imaplib.IMAP4_SSL, mailbox: str, criteria: str) -> List[str]:
    status, _ = connection.select(mailbox)
    if status != "OK":
        raise RuntimeError(f"Unable to select mailbox {mailbox}")
    status, data = connection.search(None, criteria)
    if status != "OK":
        raise RuntimeError("Failed to search mailbox")
    ids = data[0].split()
    return [msg_id.decode("utf-8") for msg_id in ids]


def _fetch_headers(connection: imaplib.IMAP4_SSL, msg_id: str) -> Tuple[str, str, str]:
    status, data = connection.fetch(msg_id, "(RFC822.HEADER)")
    if status != "OK" or not data:
        raise RuntimeError(f"Failed to fetch message {msg_id}")
    raw = data[0][1]
    message = message_from_bytes(raw)
    subject = _decode_header(message.get("Subject", ""))
    sender = _decode_header(message.get("From", ""))
    date = message.get("Date", "")
    return subject, sender, date


def _ensure_mailbox(connection: imaplib.IMAP4_SSL, mailbox: str) -> None:
    status, data = connection.list()
    if status != "OK":
        raise RuntimeError("Failed to list mailboxes")
    mailboxes = [line.decode("utf-8") for line in data if line]
    if any(mailbox in line for line in mailboxes):
        return
    LOGGER.info("Creating mailbox %s", mailbox)
    create_status, _ = connection.create(mailbox)
    if create_status != "OK":
        raise RuntimeError(f"Failed to create mailbox {mailbox}")


def _move_messages(
    connection: imaplib.IMAP4_SSL,
    mailbox: str,
    message_ids: Iterable[str],
    destination: str,
) -> int:
    _ensure_mailbox(connection, destination)
    moved = 0
    for msg_id in message_ids:
        status, _ = connection.copy(msg_id, destination)
        if status == "OK":
            connection.store(msg_id, "+FLAGS", "(\\Deleted)")
            moved += 1
    if moved:
        connection.expunge()
    return moved


def build_report(rows: List[Tuple[str, str, str]]) -> str:
    lines = ["# Daily Email Triage Report", "", f"Generated: {datetime.now():%Y-%m-%d %H:%M:%S}", ""]
    if not rows:
        lines.append("No unread or unreplied messages found.")
        return "\n".join(lines)
    lines.append("| Subject | From | Date |")
    lines.append("| --- | --- | --- |")
    for subject, sender, date in rows:
        lines.append(f"| {subject} | {sender} | {date} |")
    return "\n".join(lines)


def run_triage(config: Dict[str, Any]) -> int:
    host = _get_config_value(config, "imap_host")
    port = int(_get_config_value(config, "imap_port", "993"))
    username = _get_config_value(config, "username")
    password = _get_config_value(config, "password")
    mailbox = config.get("mailbox", "INBOX")
    criteria = config.get("criteria", "OR UNSEEN UNANSWERED")
    max_items = int(config.get("max_items", 50))
    report_path = config.get("report_path")
    move_to_folder = config.get("move_to_folder")

    with imaplib.IMAP4_SSL(host, port) as connection:
        connection.login(username, password)
        msg_ids = _imap_search(connection, mailbox, criteria)
        if max_items:
            msg_ids = msg_ids[:max_items]
        rows = [_fetch_headers(connection, msg_id) for msg_id in msg_ids]

        if move_to_folder:
            moved = _move_messages(connection, mailbox, msg_ids, move_to_folder)
            LOGGER.info("Moved %s message(s) to %s", moved, move_to_folder)

    report = build_report(rows)
    print(report)

    if report_path:
        path = Path(report_path)
        path.write_text(report, encoding="utf-8")
        LOGGER.info("Report written to %s", path)

    return len(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Daily email triage for unread/unreplied messages.")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config.json"),
        help="Path to JSON config file (default: config.json)",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)
    config = _load_config(args.config)
    total = run_triage(config)
    LOGGER.info("Found %s unread/unreplied message(s)", total)


if __name__ == "__main__":
    main()
