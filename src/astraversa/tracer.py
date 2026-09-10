import os
from collections.abc import Callable, Iterable
from queue import Empty, Queue
from threading import Event, Thread
from time import sleep, strftime
from typing import Any, NamedTuple, TypedDict

from psutil import AccessDenied, process_iter, NoSuchProcess

DispatcherEvent = Event()

class EventData(NamedTuple):
    name: str
    pid: int
    path: str
    source_name: str
    is_running: Callable[[], bool]

class InternalEventData(NamedTuple):
    name: str
    pid: int
    exe: str
    creation_time: float
    is_running: Callable[[], bool]
    hash: int

class Watchdog(NamedTuple):
    instance: Thread
    queue: Queue[EventData]
    signal: Event
    
    @classmethod
    def spawn(cls, known_processes: set[str]):
        """Spawn watchdog instance"""
        inst, queue, signal = spawn_process_watchdog(known_processes)
        return cls(inst, queue, signal)
    
    def set(self):
        """Set signal for watchdog instance"""
        self.signal.set()

    def has_catched(self):
        return self.signal.is_set()
    
    def consume(self, callback: Callable[[EventData], None]):
        """Consume an event"""
        return consume_process_events(self.queue, callback, signal=self.signal)

def select_known_process_event(
    executable_path: str | None,
    known_processes: Iterable[str] | set[str],
) -> str | None:
    """Return the executable basename when it matches a known process name."""
    if not executable_path:
        return None

    basename = os.path.basename(os.fspath(executable_path)).lower()
    allowed = {name.lower() for name in known_processes}
    return basename if basename in allowed else None


def _queue_process_event(
    queue: Queue[EventData],
    known_processes: Iterable[str] | set[str],
    *,
    internal_ed: InternalEventData
) -> None:
    selected_name = select_known_process_event(internal_ed.exe or internal_ed.name, known_processes)
    if selected_name is None:
        return

    queue.put(
        EventData(
            internal_ed.name,
            internal_ed.pid,
            internal_ed.exe or internal_ed.name,
            internal_ed.name,
            internal_ed.is_running
        )
    )


def consume_process_events(
    event_queue: Queue[EventData],
    callback: Callable[[EventData], None],
    *,
    signal: Event | None = None,
) -> list[EventData]:
    """Drain queued process events on the main thread and hand each to a callback."""
    drained: list[EventData] = []
    while True:
        try:
            event = event_queue.get_nowait()
        except Empty:
            break

        drained.append(event)
        callback(event)

    if signal is not None:
        signal.clear()
    return drained


def spawn_process_watchdog(
    known_processes: Iterable[str] | set[str],
    *,
    event_queue: Queue[EventData] | None = None,
    signal: Event | None = None,
) -> tuple[Thread, Queue[EventData], Event]:
    """Start a watcher thread that emits only known process events to the main thread."""
    DispatcherEvent.set()
    queue = event_queue or Queue()
    main_signal = signal or Event()
    seen: dict[int, InternalEventData] = {}

    def _watch_process_creation() -> None:
        while DispatcherEvent.is_set():
            for process in process_iter():
                try:
                    with process.oneshot():
                        name, create_time = process.name(), process.create_time()
                        intp = InternalEventData(
                            process.name(),
                            process.pid,
                            process.exe(),
                            process.create_time(),
                            process.is_running,
                            hash(f"{name}/{create_time}")
                        )
                except (AccessDenied, NoSuchProcess):
                    continue

                if intp.pid in seen:
                    pre = seen[intp.pid]
                    if pre.is_running() is True and pre.hash == intp.hash:
                        continue

                # print(f"{strftime("[%H:%M:%S]")} New process: {intp['name']} ({intp['pid']})")
                _queue_process_event(
                    queue,
                    known_processes,
                    internal_ed=intp
                )
                seen[intp.pid] = intp

                if not queue.empty():
                    main_signal.set()
            sleep(1)

    thread = Thread(target=_watch_process_creation, daemon=True)
    thread.start()
    return thread, queue, main_signal
