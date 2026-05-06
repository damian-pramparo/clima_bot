from __future__ import annotations

import argparse
import asyncio
import csv
import json
import random
import statistics
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx


USER_NORTE = "11111111-1111-1111-1111-111111111111"
FIELD_NORTE = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
EVENT_TYPES = ("storm", "rain", "frost", "hail", "heat_wave")


@dataclass(frozen=True)
class RequestResult:
    ts: float
    method: str
    path: str
    status_code: int | None
    latency_ms: float
    ok: bool
    error: str
    payload: str


async def timed_request(
    client: httpx.AsyncClient,
    method: str,
    path: str,
    *,
    json_body: dict[str, Any] | None = None,
) -> RequestResult:
    started = time.perf_counter()
    payload = json.dumps(json_body, sort_keys=True) if json_body else ""
    try:
        response = await client.request(method, path, json=json_body)
        latency_ms = (time.perf_counter() - started) * 1000
        return RequestResult(
            ts=time.time(),
            method=method,
            path=path,
            status_code=response.status_code,
            latency_ms=latency_ms,
            ok=response.status_code < 500,
            error="" if response.status_code < 500 else response.text[:500],
            payload=payload,
        )
    except Exception as exc:
        latency_ms = (time.perf_counter() - started) * 1000
        return RequestResult(
            ts=time.time(),
            method=method,
            path=path,
            status_code=None,
            latency_ms=latency_ms,
            ok=False,
            error=repr(exc),
            payload=payload,
        )


def weather_payload(unique: bool) -> dict[str, Any]:
    event_at = datetime.now(timezone.utc) + timedelta(
        days=random.randint(1, 30),
        minutes=random.randint(0, 1440),
    )
    event_type = random.choice(EVENT_TYPES)
    if unique:
        source = f"stress_damian_{uuid4()}"
    else:
        source = "stress_damian_duplicate_probe"
        event_at = datetime(2099, 1, 1, 12, 0, tzinfo=timezone.utc)
        event_type = "storm"

    return {
        "field_id": FIELD_NORTE,
        "event_date": event_at.isoformat(),
        "event_type": event_type,
        "probability": random.randint(1, 100),
        "source": source,
    }


def alert_payload() -> dict[str, Any]:
    return {
        "user_id": USER_NORTE,
        "field_id": FIELD_NORTE,
        "event_type": random.choice(EVENT_TYPES),
        "threshold": random.randint(1, 100),
        "active": True,
    }


async def worker(
    client: httpx.AsyncClient,
    stop_at: float,
    results: list[RequestResult],
    duplicate_ratio: float,
) -> None:
    while time.perf_counter() < stop_at:
        choice = random.random()
        if choice < 0.45:
            result = await timed_request(
                client,
                "POST",
                "/weather-events",
                json_body=weather_payload(unique=random.random() >= duplicate_ratio),
            )
        elif choice < 0.65:
            result = await timed_request(client, "POST", "/alerts", json_body=alert_payload())
        elif choice < 0.85:
            result = await timed_request(client, "POST", "/alerts/evaluate")
        elif choice < 0.95:
            result = await timed_request(client, "GET", "/notifications")
        else:
            result = await timed_request(client, "GET", "/health")

        results.append(result)
        await asyncio.sleep(random.uniform(0, 0.02))


async def sample_resources(
    stop_at: float,
    output_file: Path,
    *,
    pid: int | None,
    docker_container: str | None,
    interval_seconds: float,
) -> None:
    with output_file.open("w", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["ts", "source", "cpu_percent", "memory_mb", "raw"],
        )
        writer.writeheader()
        while time.perf_counter() < stop_at:
            sample = get_resource_sample(pid=pid, docker_container=docker_container)
            writer.writerow(sample)
            file.flush()
            await asyncio.sleep(interval_seconds)


def get_resource_sample(*, pid: int | None, docker_container: str | None) -> dict[str, Any]:
    if docker_container:
        return get_docker_sample(docker_container)
    if pid:
        return get_pid_sample(pid)
    return {
        "ts": time.time(),
        "source": "none",
        "cpu_percent": "",
        "memory_mb": "",
        "raw": "pass --pid or --docker-container to collect resource usage",
    }


def get_pid_sample(pid: int) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            ["ps", "-o", "%cpu=,rss=", "-p", str(pid)],
            check=True,
            capture_output=True,
            text=True,
        )
        raw = completed.stdout.strip()
        cpu_text, rss_text = raw.split()
        return {
            "ts": time.time(),
            "source": f"pid:{pid}",
            "cpu_percent": float(cpu_text),
            "memory_mb": round(int(rss_text) / 1024, 2),
            "raw": raw,
        }
    except Exception as exc:
        return {"ts": time.time(), "source": f"pid:{pid}", "cpu_percent": "", "memory_mb": "", "raw": repr(exc)}


def get_docker_sample(container: str) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            ["docker", "stats", "--no-stream", "--format", "json", container],
            check=True,
            capture_output=True,
            text=True,
        )
        raw = completed.stdout.strip()
        data = json.loads(raw)
        return {
            "ts": time.time(),
            "source": f"docker:{container}",
            "cpu_percent": data.get("CPUPerc", "").replace("%", ""),
            "memory_mb": data.get("MemUsage", "").split(" / ")[0],
            "raw": raw,
        }
    except Exception as exc:
        return {
            "ts": time.time(),
            "source": f"docker:{container}",
            "cpu_percent": "",
            "memory_mb": "",
            "raw": repr(exc),
        }


def write_requests_csv(output_file: Path, results: list[RequestResult]) -> None:
    with output_file.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=RequestResult.__dataclass_fields__.keys())
        writer.writeheader()
        for result in results:
            writer.writerow(result.__dict__)


def print_summary(results: list[RequestResult]) -> None:
    latencies = [result.latency_ms for result in results]
    failures = [result for result in results if not result.ok]
    by_status: dict[str, int] = {}
    by_endpoint: dict[str, int] = {}
    for result in results:
        status_key = str(result.status_code)
        endpoint_key = f"{result.method} {result.path} {result.status_code}"
        by_status[status_key] = by_status.get(status_key, 0) + 1
        by_endpoint[endpoint_key] = by_endpoint.get(endpoint_key, 0) + 1

    if not latencies:
        print("No requests completed.")
        return

    sorted_latencies = sorted(latencies)
    p95_index = max(int(len(sorted_latencies) * 0.95) - 1, 0)
    p99_index = max(int(len(sorted_latencies) * 0.99) - 1, 0)

    print("Stress test summary")
    print(f"requests_total={len(results)}")
    print(f"requests_failed={len(failures)}")
    print(f"status_codes={by_status}")
    print(f"endpoint_status={by_endpoint}")
    print(f"latency_avg_ms={statistics.mean(latencies):.2f}")
    print(f"latency_p95_ms={sorted_latencies[p95_index]:.2f}")
    print(f"latency_p99_ms={sorted_latencies[p99_index]:.2f}")
    print(f"latency_max_ms={max(latencies):.2f}")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Stress test para la API de alertas climaticas.")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--concurrency", type=int, default=20)
    parser.add_argument("--duplicate-ratio", type=float, default=0.25)
    parser.add_argument("--timeout", type=float, default=10)
    parser.add_argument("--pid", type=int)
    parser.add_argument("--docker-container")
    parser.add_argument("--resource-interval", type=float, default=2)
    parser.add_argument("--output-dir", default="stress_test_damian/results")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    run_id = time.strftime("%Y%m%d_%H%M%S")
    requests_file = output_dir / f"requests_{run_id}.csv"
    resources_file = output_dir / f"resources_{run_id}.csv"

    stop_at = time.perf_counter() + args.duration
    results: list[RequestResult] = []

    async with httpx.AsyncClient(base_url=args.base_url, timeout=args.timeout) as client:
        tasks = [
            asyncio.create_task(worker(client, stop_at, results, args.duplicate_ratio))
            for _ in range(args.concurrency)
        ]
        tasks.append(
            asyncio.create_task(
                sample_resources(
                    stop_at,
                    resources_file,
                    pid=args.pid,
                    docker_container=args.docker_container,
                    interval_seconds=args.resource_interval,
                )
            )
        )
        await asyncio.gather(*tasks)

    write_requests_csv(requests_file, results)
    print_summary(results)
    print(f"requests_csv={requests_file}")
    print(f"resources_csv={resources_file}")


if __name__ == "__main__":
    asyncio.run(main())
