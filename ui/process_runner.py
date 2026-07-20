"""Threaded subprocess runner used by the desktop UI."""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ProcessEvent:
    kind: str
    message: str = ""
    state: str = ""
    script_name: str = ""
    exit_code: Optional[int] = None


class ProcessRunner:
    """Run one project script at a time without blocking the UI."""

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.events: "queue.Queue[ProcessEvent]" = queue.Queue()
        self.process: Optional[subprocess.Popen[str]] = None
        self.current_script = ""
        self._lock = threading.Lock()
        self._stop_requested = False

    def is_running(self) -> bool:
        with self._lock:
            return self.process is not None and self.process.poll() is None

    def start_script(self, script_name: str, initial_input: str = "") -> bool:
        script_path = self.project_root / script_name

        if self.is_running():
            self.events.put(ProcessEvent(
                kind="state",
                state="running",
                message="A task is already running. Stop it before starting another.",
                script_name=self.current_script,
            ))
            return False

        if not script_path.exists():
            self.events.put(ProcessEvent(
                kind="state",
                state="failed",
                message=f"Missing script: {script_name}",
                script_name=script_name,
            ))
            return False

        self.current_script = script_name
        self._stop_requested = False
        worker = threading.Thread(
            target=self._run_script,
            args=(script_name, initial_input),
            daemon=True,
        )
        worker.start()
        return True

    def send_input(self, text: str) -> bool:
        if not self.is_running() or self.process is None or self.process.stdin is None:
            self.events.put(ProcessEvent(
                kind="state",
                state="idle",
                message="No running task is waiting for input.",
                script_name=self.current_script,
            ))
            return False

        if not text.endswith("\n"):
            text += "\n"

        try:
            self.process.stdin.write(text)
            self.process.stdin.flush()
        except OSError as error:
            self.events.put(ProcessEvent(
                kind="state",
                state="failed",
                message=f"Could not send input: {error}",
                script_name=self.current_script,
            ))
            return False

        return True

    def stop(self) -> None:
        if not self.is_running() or self.process is None:
            self.events.put(ProcessEvent(
                kind="state",
                state="idle",
                message="No running task to stop.",
                script_name=self.current_script,
            ))
            return

        self._stop_requested = True
        pid = self.process.pid

        try:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
            else:
                self.process.terminate()
        except OSError:
            self.process.kill()

    def _run_script(self, script_name: str, initial_input: str) -> None:
        self.events.put(ProcessEvent(
            kind="state",
            state="running",
            message=f"Running {script_name}",
            script_name=script_name,
        ))

        popen_kwargs = {
            "cwd": str(self.project_root),
            "stdin": subprocess.PIPE,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "text": True,
            "bufsize": 1,
        }

        if os.name != "nt":
            popen_kwargs["start_new_session"] = True

        try:
            process = subprocess.Popen(
                [sys.executable, script_name],
                **popen_kwargs,
            )
        except OSError as error:
            self.events.put(ProcessEvent(
                kind="state",
                state="failed",
                message=f"Could not start {script_name}: {error}",
                script_name=script_name,
            ))
            return

        with self._lock:
            self.process = process

        stdout_thread = threading.Thread(
            target=self._read_stream,
            args=(process.stdout, "stdout", script_name),
            daemon=True,
        )
        stderr_thread = threading.Thread(
            target=self._read_stream,
            args=(process.stderr, "stderr", script_name),
            daemon=True,
        )
        stdout_thread.start()
        stderr_thread.start()

        if initial_input:
            self.send_input(initial_input)

        exit_code = process.wait()
        stdout_thread.join(timeout=1)
        stderr_thread.join(timeout=1)

        with self._lock:
            self.process = None

        if self._stop_requested:
            state = "stopped"
            message = f"Stopped {script_name}."
        elif exit_code == 0:
            state = "completed"
            message = f"Completed {script_name}."
        else:
            state = "failed"
            message = f"{script_name} exited with code {exit_code}."

        self.events.put(ProcessEvent(
            kind="state",
            state=state,
            message=message,
            script_name=script_name,
            exit_code=exit_code,
        ))

    def _read_stream(self, stream, stream_name: str, script_name: str) -> None:
        if stream is None:
            return

        for line in iter(lambda: stream.read(1), ""):
            self.events.put(ProcessEvent(
                kind=stream_name,
                message=line,
                state="running",
                script_name=script_name,
            ))
