#!/usr/bin/env python3
"""
MarcoAI – LLM Gateway integration smoke-test
─────────────────────────────────────────────
Run this script (outside Docker) to verify that every provider tier
is reachable and the fallback chain works correctly.

Usage:
    cd /mnt/AI/marcoai/backend
    python3 scripts/test_gateway.py

Requirements:
    • A valid .env file in the repository root (../../.env relative to this script)
    • Internet access to reach the LLM APIs

The script does NOT require the FastAPI server to be running.
"""

import asyncio
import os
import sys
from pathlib import Path

# ── Load .env from repo root ──────────────────────────────────────────────────
env_path = Path(__file__).resolve().parents[2] / ".env"
if not env_path.exists():
    print(f"ERROR: .env not found at {env_path}")
    sys.exit(1)

# Inject env vars manually (pydantic-settings will also pick them up)
for line in env_path.read_text().splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, _, val = line.partition("=")
    val = val.strip().strip('"').strip("'")
    os.environ.setdefault(key.strip(), val)

# Now import the gateway (needs env vars to be set first)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.llm_gateway import TaskTier, gateway   # noqa: E402


TEST_MESSAGE = "Di 'Hola, soy Marco' en una sola frase."

SYSTEM = {
    "role": "system",
    "content": "Eres Marco, un asistente personal conciso. Responde siempre en español."
}

TIERS = [TaskTier.FAST, TaskTier.STANDARD, TaskTier.INTELLIGENT]

CYAN  = "\033[96m"
GREEN = "\033[92m"
RED   = "\033[91m"
RESET = "\033[0m"
BOLD  = "\033[1m"


async def main() -> None:
    print(f"\n{BOLD}═══ MarcoAI LLM Gateway – Smoke Test ═══{RESET}\n")

    results: list[tuple[str, bool, str]] = []

    for tier in TIERS:
        messages = [SYSTEM, {"role": "user", "content": TEST_MESSAGE}]
        print(f"{CYAN}▶ Testing tier: {tier.value.upper()}{RESET}")
        try:
            response = await gateway.complete(messages, tier=tier, max_tokens=80)
            snippet = response[:120].replace("\n", " ")
            print(f"  {GREEN}OK{RESET}  \"{snippet}...\"\n")
            results.append((tier.value, True, snippet))
        except Exception as exc:
            print(f"  {RED}✗ FAIL{RESET}  {exc}\n")
            results.append((tier.value, False, str(exc)))

    # ── Summary ────────────────────────────────────────────────────────────────
    print(f"{BOLD}═══ Summary ═══{RESET}")
    for tier_name, ok, msg in results:
        status = f"{GREEN}PASS{RESET}" if ok else f"{RED}FAIL{RESET}"
        print(f"  {tier_name:<14} [{status}]  {msg[:80]}")

    failures = sum(1 for _, ok, _ in results if not ok)
    if failures:
        print(f"\n{RED}{failures} tier(s) failed.{RESET}")
        sys.exit(1)
    else:
        print(f"\n{GREEN}All tiers passed! ✓{RESET}\n")


if __name__ == "__main__":
    asyncio.run(main())
