"""OpenTelemetry tracing for the Experiment 2 runs.

One trace per trial. The reference agent opens a ``trial`` span when the
runner prepares a trial and child spans for every model call, embedding call,
retrieval and tool round. Attribute names follow the OpenTelemetry GenAI
semantic conventions where they exist (``gen_ai.*``; Development status at the
time of writing); the experiment's own attributes are under ``e2.*`` and
``circumstances.*``.

Spans go to a JSON Lines file beside the sealed bundles
(``results/<run>/telemetry/<condition>.spans.jsonl``), so the record travels
with the result and needs no collector. When the standard
``OTEL_EXPORTER_OTLP_ENDPOINT`` (or ``OTEL_EXPORTER_OTLP_TRACES_ENDPOINT``)
variable is set, they are also sent there over OTLP/HTTP.

The file schema is one span per line, close to Kodama's own span dump
(``backend/internal/telemetry/sink.go``) so one summary reads both::

    {"trace_id", "span_id", "parent_span_id", "name", "kind",
     "start_unix_nano", "end_unix_nano", "status": {"code", "description"},
     "attributes": {...}, "events": [{"name", "time_unix_nano", "attributes"}]}

No message content, prompt, key or host name is recorded.
"""

from __future__ import annotations

import json
import os
import threading
from collections.abc import Sequence
from pathlib import Path
from typing import IO

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    SpanExporter,
    SpanExportResult,
)

TRACER_NAME = "stale-but-on-time.e2"


def _value(v: object) -> object:
    if isinstance(v, tuple):
        return list(v)
    return v


def span_to_dict(span: ReadableSpan) -> dict:
    ctx = span.get_span_context()
    parent = span.parent
    return {
        "trace_id": format(ctx.trace_id, "032x"),
        "span_id": format(ctx.span_id, "016x"),
        "parent_span_id": format(parent.span_id, "016x") if parent else "",
        "name": span.name,
        "kind": span.kind.name.lower(),
        "start_unix_nano": span.start_time,
        "end_unix_nano": span.end_time,
        "status": {
            "code": span.status.status_code.name.lower(),
            "description": span.status.description or "",
        },
        "attributes": {k: _value(v) for k, v in (span.attributes or {}).items()},
        "events": [
            {
                "name": e.name,
                "time_unix_nano": e.timestamp,
                "attributes": {k: _value(v) for k, v in (e.attributes or {}).items()},
            }
            for e in span.events
        ],
    }


class JsonLinesSpanExporter(SpanExporter):
    """Appends one JSON object per ended span to a file."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._file: IO[str] | None = path.open("a", encoding="utf-8")

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        with self._lock:
            if self._file is None:
                return SpanExportResult.FAILURE
            for span in spans:
                self._file.write(json.dumps(span_to_dict(span), sort_keys=True) + "\n")
            self._file.flush()
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        with self._lock:
            if self._file is not None:
                self._file.close()
                self._file = None

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True


def otlp_configured() -> bool:
    return bool(
        os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
        or os.environ.get("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
    )


def install(spans_file: Path, resource: dict[str, str]) -> TracerProvider:
    """A fresh tracer provider writing to ``spans_file`` (and OTLP if configured).

    Each condition gets its own provider and file; call ``shutdown`` on it
    when the condition is done so every span is written.
    """
    provider = TracerProvider(
        resource=Resource.create({"service.name": TRACER_NAME, **resource})
    )
    # Batched: the file is written from a background thread, so writing spans
    # adds nothing measurable to the reply-path timings.
    provider.add_span_processor(BatchSpanProcessor(JsonLinesSpanExporter(spans_file)))
    if otlp_configured():
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    return provider


def tracer(provider: trace.TracerProvider | None) -> trace.Tracer:
    """The experiment tracer; a no-op tracer when no provider was installed."""
    if provider is None:
        return trace.NoOpTracer()
    return provider.get_tracer(TRACER_NAME)


def read_spans(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
