"""events_demo.py -- A tiny, heavily commented example of event-driven architecture.

WHAT THIS FILE TEACHES
----------------------
Most beginner programs are written as one function calling another directly:

    def add_task(...):
        save_task(...)          # the "publisher" must know every next step
        send_email(...)
        update_stats(...)
        write_log(...)

Every new side effect means editing `add_task`. The task logic and the side
effects are *tightly coupled*.

Event-driven architecture flips that around. The app announces a fact --
"a task was added" -- and interested parties *subscribe* to that fact:

       TaskStore                    EventBus                    Subscribers
      (publisher)                 (the registry)                 (handlers)
          |                            |                             |
          |  publish(TaskAdded(...))   |                             |
          |--------------------------->|                             |
          |                            |--- call log_event() ------->|  logger
          |                            |--- call send_email() ------>|  notifier
          |                            |--- call award_points() ---->|  rewards
          |                            |                             |
          |  <-- publish returns ------|  (all handlers have run)    |

The publisher only knows the EventBus. Subscribers only know the event.
Nobody has to know everybody else, so you can add or remove behaviour
without touching the code that adds tasks.

THE FOUR PIECES
---------------
1. EVENT      -- an immutable record that something happened: TaskAdded.
2. PUBLISHER  -- code that says "this happened": TaskStore.publish(...).
3. SUBSCRIBER -- a function that reacts to one event type.
4. EVENT BUS  -- the registry that connects publishers to subscribers.

This demo is deliberately synchronous and in-process: `publish()` calls each
handler immediately, one after another, and waits for them to finish. That is
the easiest version to reason about. Real systems often put a queue or a
message broker (Kafka, RabbitMQ, Redis Streams) between the publisher and the
subscribers, which makes delivery asynchronous and durable -- but the shape of
the code is the same.

Run it with:

    uv run python events_demo.py

(The output uses Rich -- already a dependency of this repo -- for colour,
panels and tables. The architecture itself is plain Python: Rich is only the
presentation layer.)
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field, fields
from datetime import datetime, timezone
from typing import Any, Callable

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

# ---------------------------------------------------------------------------
# PRESENTATION HELPERS -- this section is about looking good, not architecture.
# The bus and handlers call these helpers directly to keep the demo short.
# In a real app, keep Rich out of the domain: have the bus publish to a logger
# (or accept a renderer callback) and let the UI subscribe to events instead.
# ---------------------------------------------------------------------------
# `legacy_windows=False` prefers ANSI colour on Windows. Modern terminals
# (Windows Terminal, VS Code, PowerShell 7) render it; the old Win32 path
# silently drops colour when output is redirected.
console = Console(highlight=False, legacy_windows=False)

EVENT_COLOURS = {
    "TaskAdded": "bright_green",
    "TaskCompleted": "bright_blue",
}

SUBSCRIBER_COLOURS = {
    "log": "bright_blue",
    "notify": "bright_green",
    "rewards": "yellow",
    "analytics": "bright_cyan",
}


def section(title: str, subtitle: str = "") -> None:
    """Print a full-width section divider with an optional explanation."""
    console.print()
    console.print(Rule(f"[bold white]{title}[/]", style="dim cyan"))
    if subtitle:
        console.print(f"[dim]{subtitle}[/]")


def subscriber_line(tag: str, message: str) -> None:
    """One styled line from a subscriber, aligned by subscriber name."""
    colour = SUBSCRIBER_COLOURS[tag]
    console.print(f"  [bold {colour}]{tag:>9}[/]  {message}")


# ---------------------------------------------------------------------------
# 1. EVENTS -- the vocabulary of things that can happen
# ---------------------------------------------------------------------------
# Good event names are past-tense facts: "TaskAdded", not "AddTask".
# An event describes something that already happened. It is a noun, not a
# command, and it is immutable: handlers must not rewrite history.
#
# `frozen=True` makes the dataclass read-only, so a handler cannot accidentally
# change an event another handler will receive a moment later. `kw_only=True`
# lets subclasses add required fields after the inherited defaulted timestamp
# (dataclasses otherwise reject "non-default after default").
@dataclass(frozen=True, kw_only=True)
class Event:
    """Base class for every event. All events carry a timestamp."""

    occurred_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@dataclass(frozen=True)
class TaskAdded(Event):
    """A task was successfully added to the list."""

    title: str
    priority: int = 1  # 1 = normal, 3 = urgent


@dataclass(frozen=True)
class TaskCompleted(Event):
    """A task was marked as done."""

    title: str
    minutes_spent: int = 0


def describe_event(event: Event) -> str:
    """Render an event's payload as `field=value` pairs for the screen.

    `occurred_at` is shown separately in the history table, so we skip it
    here. This is presentation code, not part of the event model.
    """
    parts = []
    for event_field in fields(event):
        if event_field.name == "occurred_at":
            continue
        parts.append(f"{event_field.name}={getattr(event, event_field.name)!r}")
    return "  ".join(parts)


# Handlers are just callables that take one event and return None.
# Type aliases make the bus a little easier to read.
Handler = Callable[[Any], None]


# ---------------------------------------------------------------------------
# 2. THE EVENT BUS -- the only thing publishers and subscribers share
# ---------------------------------------------------------------------------
class EventBus:
    """A minimal publish/subscribe registry.

    The bus keeps a dictionary mapping an event *class* to a list of handlers:

        TaskAdded     -> [log_event, send_email]
        TaskCompleted -> [log_event, award_points, record_analytics]

    `publish()` looks up the event's class, then calls every handler for that
    class. This is sometimes called "fan-out": one event, many reactions.
    """

    def __init__(self) -> None:
        # defaultdict gives us an empty list for unseen event types, so we
        # never have to check "does this key exist?" before appending.
        self._handlers: dict[type[Event], list[Handler]] = defaultdict(list)

        # Keeping a history is optional, but it is useful for debugging and
        # for demonstrating that events really are just data. A real app
        # might persist this to disk or ship it to an event log.
        self.history: list[Event] = []

    def subscribe(self, event_type: type[Event], handler: Handler) -> Callable[[], None]:
        """Register `handler` for events of `event_type`.

        Returns an *unsubscribe* function. Calling it removes the handler.
        Returning the "off switch" is a nice pattern: the subscriber decides
        when to stop listening, and the bus does not need a separate API for
        every case.
        """
        self._handlers[event_type].append(handler)
        console.print(
            f"  [bold magenta]bus[/] [green]subscribed[/] "
            f"[white]{handler.__name__}[/] [dim]->[/] "
            f"[bold cyan]{event_type.__name__}[/]"
        )

        def unsubscribe() -> None:
            self._handlers[event_type].remove(handler)
            console.print(
                f"  [bold magenta]bus[/] [red]unsubscribed[/] "
                f"[white]{handler.__name__}[/] [dim]from[/] "
                f"[bold cyan]{event_type.__name__}[/]"
            )

        return unsubscribe

    def publish(self, event: Event) -> None:
        """Call every handler subscribed to this event's type.

        Notes for students:
        * `type(event)` is used, not `isinstance`. That means an event is
          delivered only to handlers registered for that exact class. (Using
          isinstance would let a subscriber for `Event` receive every event;
          try it as an exercise.)
        * We iterate over a *copy* of the handler list (`list(...)`) so that a
          handler may subscribe or unsubscribe while the event is being
          delivered without breaking the loop.
        * One broken handler must not stop the others. We catch exceptions
          per handler and report them. In a real system you would log these
          to a proper logger or send them to an error tracker.
        * The Rich panel below is presentation. A production bus should not
          know about the console; this demo renders here so the flow is
          visible while reading the file from top to bottom.
        """
        self.history.append(event)
        handlers = list(self._handlers[type(event)])
        event_name = type(event).__name__
        colour = EVENT_COLOURS.get(event_name, "cyan")

        # The panel is the announcement: "this event exists, and this is its
        # payload". The handler lines below it are the reactions.
        title = Text.assemble(
            ("EVENT  ", "bold white"),
            (event_name, f"bold {colour}"),
        )
        console.print()
        console.print(
            Panel(
                Text(describe_event(event), style="white"),
                title=title,
                subtitle=f"[dim]{len(handlers)} subscriber(s)[/]",
                border_style=colour,
                box=box.ROUNDED,
                padding=(0, 2),
            )
        )

        for handler in handlers:
            try:
                handler(event)
            except Exception as exc:  # noqa: BLE001 -- demo: isolate failures
                console.print(
                    f"  [bold red]bus[/] [red]! {handler.__name__} failed:[/] "
                    f"[red dim]{exc}[/]"
                )


# ---------------------------------------------------------------------------
# 3. SUBSCRIBERS -- independent reactions to what happened
# ---------------------------------------------------------------------------
# A subscriber should do one job. If it needs three jobs, write three
# subscribers. That way each one can be tested, removed, or replaced alone.
#
# Notice that none of these functions import or call TaskStore. They only
# receive an event. They do not return anything useful: events are
# fire-and-forget, not request/response. If a caller needs an answer, a direct
# function call is the right tool -- not an event.


def log_event(event: Event) -> None:
    """Log every task event. This subscriber is registered twice: once for
    TaskAdded and once for TaskCompleted."""
    stamp = event.occurred_at.strftime("%H:%M:%S")
    subscriber_line(
        "log",
        f"[dim]{stamp}[/] [bold]{type(event).__name__}[/] "
        f"[dim]{describe_event(event)}[/]",
    )


def celebrate_added(event: TaskAdded) -> None:
    """React to a new task. This is the sort of place you would send a
    confirmation email, push a notification, or update a UI."""
    subscriber_line(
        "notify",
        f"New task queued: [bold]{event.title!r}[/] "
        f"[dim](priority {event.priority})[/]",
    )


def award_points(event: TaskCompleted) -> None:
    """A 'gamification' subscriber: completing a task earns points.

    It knows nothing about the task store, the logger, or analytics. It could
    be deleted in one line and the rest of the app would still work.
    """
    points = 10 + event.minutes_spent // 5
    subscriber_line(
        "rewards",
        f"[bold]+{points}[/] points for finishing [bold]{event.title!r}[/]",
    )


def record_analytics(event: TaskCompleted) -> None:
    """A second, independent reaction to the same event."""
    subscriber_line(
        "analytics",
        f"recorded [bold]{event.minutes_spent}[/] minutes on "
        f"[bold]{event.title!r}[/]",
    )


# ---------------------------------------------------------------------------
# 4. THE PUBLISHER -- application logic that announces facts
# ---------------------------------------------------------------------------
class TaskStore:
    """Owns the task list and publishes events after state changes.

    Two important rules of thumb:
    * Publish *after* the state change succeeds. An event is a report that
      something happened, not a request to make it happen.
    * Keep the publisher focused on its own job. It should not know who is
      listening or what they do. That is the whole point of the bus.
    """

    def __init__(self, bus: EventBus) -> None:
        self._bus = bus
        self._tasks: dict[str, dict] = {}

    def add_task(self, title: str, priority: int = 1) -> None:
        if not title.strip():
            raise ValueError("title cannot be empty")

        # 1. Do the actual work.
        self._tasks[title] = {"title": title, "priority": priority, "done": False}

        # 2. Announce what changed. We do not call the logger, the notifier,
        #    or the rewards system directly -- we do not even import them.
        self._bus.publish(TaskAdded(title=title, priority=priority))

    def complete_task(self, title: str, minutes_spent: int = 0) -> None:
        if title not in self._tasks:
            raise KeyError(f"unknown task: {title}")

        self._tasks[title]["done"] = True
        self._bus.publish(
            TaskCompleted(title=title, minutes_spent=minutes_spent)
        )


# ---------------------------------------------------------------------------
# 5. WIRING IT TOGETHER -- the "composition root"
# ---------------------------------------------------------------------------
def main() -> None:
    """Build the objects, connect subscribers, then use the app.

    The wiring lives here, in one place, instead of being scattered through
    the business logic. This function is sometimes called the composition
    root: the one spot that knows about all the pieces.
    """
    intro = Text.assemble(
        ("Publisher", "bold yellow"),
        ("  -- event -->  ", "dim"),
        ("EventBus", "bold magenta"),
        ("  -- fan-out -->  ", "dim"),
        ("Subscribers", "bold bright_green"),
    )
    intro.append(
        "\n\nTaskStore announces what happened; the bus calls every subscriber."
    )
    intro.append(
        "\nThe publisher and the subscribers never import each other.", style="dim"
    )
    console.print(
        Panel(
            intro,
            title="[bold]Event-Driven Architecture[/]",
            subtitle="[dim]one fact, many reactions[/]",
            border_style="bright_cyan",
            box=box.ROUNDED,
            padding=(0, 2),
        )
    )

    bus = EventBus()

    section(
        "1 - Wiring the composition root",
        "The only place that knows about every subscriber.",
    )
    bus.subscribe(TaskAdded, log_event)
    bus.subscribe(TaskCompleted, log_event)
    bus.subscribe(TaskAdded, celebrate_added)
    stop_rewards = bus.subscribe(TaskCompleted, award_points)
    bus.subscribe(TaskCompleted, record_analytics)

    store = TaskStore(bus)

    section(
        "2 - Adding tasks",
        "Each call publishes TaskAdded. The publisher does not know who listens.",
    )
    store.add_task("Write the report", priority=2)
    store.add_task("Water the plants")

    section(
        "3 - Completing a task",
        "One TaskCompleted event fans out to three independent subscribers.",
    )
    store.complete_task("Write the report", minutes_spent=25)

    # Demonstration: a subscriber can be removed at runtime. The publisher
    # does not change at all, which is exactly the benefit of this design.
    # `subscribe()` gave us the matching off switch when we wired it above.
    section(
        "4 - Removing a subscriber",
        "The publisher is unchanged; one reaction disappears from the fan-out.",
    )
    stop_rewards()

    # `award_points` and `record_analytics` are both still subscribed to
    # TaskCompleted, but only one of them reacts now.
    store.complete_task("Water the plants", minutes_spent=5)

    # `store` is now done, but the bus still holds references to the handlers.
    # In a long-lived process you would call the unsubscribe functions when a
    # subscriber shuts down to avoid leaks. (Here the process exits anyway.)

    section(
        "5 - Event history",
        "Events are data: a log lets you audit or replay what happened.",
    )
    history = Table(
        title="Events published in this run",
        title_style="bold white",
        box=box.SIMPLE_HEAVY,
        border_style="dim",
        header_style="bold bright_cyan",
        row_styles=["", "dim"],
    )
    history.add_column("Time", style="dim", no_wrap=True)
    history.add_column("Event", style="bold", no_wrap=True)
    history.add_column("Details", overflow="fold")

    for event in bus.history:
        event_name = type(event).__name__
        history.add_row(
            event.occurred_at.strftime("%H:%M:%S"),
            Text(event_name, style=f"bold {EVENT_COLOURS.get(event_name, 'cyan')}"),
            Text(describe_event(event)),
        )

    console.print(history)


# ---------------------------------------------------------------------------
# EXERCISES FOR STUDENTS
# ---------------------------------------------------------------------------
# 1. Add a `TaskDeleted` event and a subscriber that logs deletions. You should
#    not need to change EventBus, TaskStore's constructor, or any existing
#    subscriber.
#
# 2. Change `publish()` to use `isinstance(handler_type, ...)` matching so a
#    subscriber registered for `Event` receives every event. What are the
#    trade-offs? (Hint: order and surprise.)
#
# 3. Make handler failures visible without crashing: collect exceptions and
#    raise one `ExceptionGroup` after all handlers have run. Which behaviour is
#    better for a UI? For a payment system?
#
# 4. Add a wildcard subscription (`bus.subscribe_all(handler)`) for logging or
#    metrics. Which is simpler: wildcard handlers, or subscribing the same
#    function to each event type?
#
# 5. Replace the synchronous `publish()` with a queue and a worker thread.
#    What new problems appear? (Ordering, shutdown, exceptions, backpressure.)
#
# 6. Persist `bus.history` to a JSON file and reload it. Why is an event log
#    useful even if nothing subscribes to it today?
#
# 7. Compare this file with calling functions directly. Which version is
#    easier to unit test? Which is easier to follow when debugging?
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    main()
