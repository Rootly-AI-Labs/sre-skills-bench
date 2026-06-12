"""Split-screen TUI for benchmark progress using Rich."""

import threading
import time
from collections import defaultdict
from typing import Callable, Optional

from rich.console import Console, ConsoleOptions, Group, RenderResult
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn
from rich.table import Table
from rich.text import Text

# ---------------------------------------------------------------------------
# Global log callback (thread-safe via the GIL for simple attribute access)
# ---------------------------------------------------------------------------

_log_callback: Optional[Callable[[str], None]] = None


def set_log_callback(cb: Optional[Callable[[str], None]]) -> None:
    global _log_callback
    _log_callback = cb


def get_log_callback() -> Optional[Callable[[str], None]]:
    return _log_callback


# ---------------------------------------------------------------------------
# BenchmarkDisplay  -- Rich Live split-screen TUI
# ---------------------------------------------------------------------------

_MAX_LOG_LINES = 200
_VISIBLE_LOG_LINES = 40


class BenchmarkDisplay:
    """Real-time split-screen display: scrolling logs (left) + stats (right)."""

    def __init__(self, total_jobs: int) -> None:
        self._total_jobs = total_jobs
        self._completed = 0

        # Log buffer
        self._log_lines: list[str] = []
        self._lock = threading.Lock()

        # Per-model stats
        self._model_pass: dict[str, int] = defaultdict(int)
        self._model_fail: dict[str, int] = defaultdict(int)

        # Recent API calls (last 10)
        self._api_calls: list[dict] = []

        self._start_time = time.monotonic()

        # Rich objects (created in start())
        self._console = Console(stderr=True)
        self._progress = Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=None),
            MofNCompleteColumn(),
            console=self._console,
        )
        self._progress_task = self._progress.add_task(
            "Benchmark", total=total_jobs
        )
        self._live: Optional[Live] = None

    # -- Rich renderable protocol ---------------------------------------------
    # By implementing __rich_console__, Live's auto-refresh thread calls
    # _render() on every tick (4×/sec), keeping elapsed time and logs fresh
    # even when no new events arrive.

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        yield self._render()

    # -- public API ----------------------------------------------------------

    def start(self) -> None:
        self._live = Live(
            self,  # Live will call __rich_console__ on every refresh tick
            console=self._console,
            refresh_per_second=4,
            screen=False,
        )
        self._live.start()

    def stop(self) -> None:
        if self._live is not None:
            self._live.stop()
            self._live = None

    def on_log(self, message: str) -> None:
        with self._lock:
            self._log_lines.append(message)
            if len(self._log_lines) > _MAX_LOG_LINES:
                self._log_lines = self._log_lines[-_MAX_LOG_LINES:]
        # No manual refresh — Live's auto-refresh (4×/sec) picks up the
        # data change on the next tick, avoiding flicker from burst redraws.

    def on_api_start(self, model: str, task: str) -> None:
        """Record the start of an LLM API call."""
        with self._lock:
            self._api_calls.append({
                "model": model, "task": task,
                "start": time.monotonic(),
                "status": "running", "duration": None,
            })
            # Keep only the last 10
            if len(self._api_calls) > 10:
                self._api_calls = self._api_calls[-10:]

    def on_api_complete(self, model: str, task: str, success: bool, duration: float) -> None:
        """Record the completion of an LLM API call."""
        with self._lock:
            # Find the most recent matching "running" entry
            for entry in reversed(self._api_calls):
                if entry["model"] == model and entry["task"] == task and entry["status"] == "running":
                    entry["status"] = "done" if success else "failed"
                    entry["duration"] = duration
                    break

    def on_job_complete(self, model: str, task: str, passed: bool) -> None:
        with self._lock:
            self._completed += 1
            if passed:
                self._model_pass[model] += 1
            else:
                self._model_fail[model] += 1
        self._progress.update(self._progress_task, completed=self._completed)

    def _render(self) -> Layout:
        layout = Layout()
        layout.split_row(
            Layout(name="logs", ratio=3),
            Layout(name="stats", ratio=2, minimum_size=46),
        )

        # Left panel: scrolling logs with color-coded prefixes
        with self._lock:
            visible = self._log_lines[-_VISIBLE_LOG_LINES:]
        if visible:
            log_text = Text()
            for i, line in enumerate(visible):
                if i > 0:
                    log_text.append("\n")
                if line.startswith("[INFO]"):
                    log_text.append("[INFO]", style="green")
                    rest = line[6:]
                elif line.startswith("[WARN]"):
                    log_text.append("[WARN]", style="yellow")
                    rest = line[6:]
                elif line.startswith("[ERROR]"):
                    log_text.append("[ERROR]", style="red bold")
                    rest = line[7:]
                else:
                    log_text.append(line)
                    continue
                # Highlight PASS / FAIL in the rest of the line
                _colorize_pass_fail(log_text, rest)
        else:
            log_text = Text("(waiting for logs ...)", style="dim")
        layout["logs"].update(Panel(log_text, title="Logs", border_style="dim"))

        # Right panel: progress + model table + elapsed/rate
        stats_parts: list = []

        # Progress bar
        stats_parts.append(self._progress)

        # Model table
        table = Table(title="Model Stats", expand=True, show_edge=False)
        table.add_column("Model", style="cyan", no_wrap=True, max_width=36)
        table.add_column("Pass", style="green", justify="right")
        table.add_column("Fail", style="red", justify="right")

        with self._lock:
            models = sorted(
                set(list(self._model_pass.keys()) + list(self._model_fail.keys()))
            )
            for m in models:
                table.add_row(
                    _truncate(m, 36),
                    str(self._model_pass.get(m, 0)),
                    str(self._model_fail.get(m, 0)),
                )
        stats_parts.append(table)

        # Recent API calls table
        with self._lock:
            recent_calls = list(self._api_calls)
        if recent_calls:
            api_table = Table(title="Recent API Calls", expand=True, show_edge=False)
            api_table.add_column("Model", style="cyan", no_wrap=True, max_width=24)
            api_table.add_column("Task", no_wrap=True, max_width=12)
            api_table.add_column("", justify="center", width=2)
            api_table.add_column("Time", justify="right", width=6)
            for call in recent_calls:
                if call["status"] == "running":
                    elapsed_call = time.monotonic() - call["start"]
                    icon = "[bold yellow]~[/]"
                    dur = f"{elapsed_call:.0f}s"
                elif call["status"] == "done":
                    icon = "[green]Y[/]"
                    dur = f"{call['duration']:.1f}s" if call["duration"] is not None else "-"
                else:
                    icon = "[red]X[/]"
                    dur = f"{call['duration']:.1f}s" if call["duration"] is not None else "-"
                api_table.add_row(
                    _truncate(call["model"], 24),
                    _truncate(call["task"], 12),
                    icon,
                    dur,
                )
            stats_parts.append(api_table)

        # Elapsed / rate
        elapsed = time.monotonic() - self._start_time
        mins, secs = divmod(int(elapsed), 60)
        rate = (self._completed / elapsed * 60) if elapsed > 0 else 0.0
        footer = Text(f"\nElapsed: {mins}m {secs:02d}s\nRate: {rate:.1f} jobs/min")
        stats_parts.append(footer)

        # Combine into right panel
        layout["stats"].update(
            Panel(Group(*stats_parts), title="Progress", border_style="dim")
        )

        return layout


def _colorize_pass_fail(text: Text, s: str) -> None:
    """Append *s* to *text*, highlighting PASS in green and FAIL in red."""
    pos = 0
    for token, style in (("PASS", "green bold"), ("FAIL", "red bold")):
        while True:
            idx = s.find(token, pos)
            if idx == -1:
                break
            if idx > pos:
                text.append(s[pos:idx])
            text.append(token, style=style)
            pos = idx + len(token)
    if pos < len(s):
        text.append(s[pos:])


def _truncate(s: str, length: int) -> str:
    return s if len(s) <= length else s[: length - 1] + "\u2026"
