"""pub_sub.py - the smallest useful publish/subscribe demo, drawn with rich.

Read it in this order:

  1. Publisher / Subscriber        <- the whole idea, about 20 lines of logic
  2. the show_* helpers            <- pure presentation, ignore on a first pass
  3. the demo at the bottom        <- who creates what, and in which order

Two channels of output, deliberately kept apart:

  * colour panels  = what the *application* is doing (a message fanning out)
  * grey sys lines = what the *system* is doing underneath (queue depth, object
                     ids, thread, timings, queue bookkeeping). Unpanelled, dim
                     and single-line, so you can read the panels and still see
                     the plumbing.
"""

import os
import platform
import queue
import threading
import time

from rich import box
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# One Console shared by the whole file. Rich writes straight through when the
# target is a real terminal, so panels appear live as the code runs. A single
# object keeps width and colour decisions consistent across every panel.
console = Console()


# ---------------------------------------------------------------------------
# The system channel: greyed-out white trace lines
# ---------------------------------------------------------------------------

# Everything is timed relative to this instant, so the first line reads 0.000s
# and the numbers stay small and comparable - an absolute clock time would say
# nothing about how long each step took.
_BOOT = time.perf_counter()

# Set this to False (or run with SYS_LOG=0) to get the clean panels-only view,
# which is handy when projecting this in a talk.
SYS_LOG = os.environ.get("SYS_LOG", "1") not in ("0", "false", "no")

# Grey palette, in three steps so the channel has internal hierarchy:
#   grey30      -> the timestamp and the "sys" tag, near-invisible scaffolding
#   dim white   -> the operation name, the one thing you actually scan for
#   grey42      -> key=value facts, readable if you look, ignorable if you don't
# All three are greyscale on purpose: nothing in this channel competes with the
# panel colours for attention.
_C_DIM = "grey42"
_C_LABEL = "grey30"
_C_EVENT = "dim white"


def sys_log(event: str, **fields) -> None:
    """Print one greyed-out system line: what the machinery just did.

    Thinking: the interesting part of this function is what it prints and how
    quietly. Every line carries (a) time since start, (b) a subsystem tag,
    (c) the operation, (d) key=value facts. No prose sentences - this is a
    trace, not narration, so it stays scannable at speed.

    Thinking: fields are rendered with repr-ish str() and the whole line goes
    through escape(), because a message containing '[' would otherwise be
    parsed as rich markup and silently change the styling.
    """
    if not SYS_LOG:
        return

    elapsed = time.perf_counter() - _BOOT
    detail = "  ".join(f"{k}={v}" for k, v in fields.items())

    line = Text()
    line.append(f"{elapsed:7.3f}s", style=_C_LABEL)
    line.append("  sys  ", style=_C_LABEL)
    # max(1, ...) not a fixed field width: 'Subscriber.receive.end' is already
    # 22 chars, and a plain <22 format would jam the first field against it.
    line.append(event + " " * max(1, 23 - len(event)), style=_C_EVENT)
    line.append(detail, style=_C_DIM)

    # soft_wrap=True: never wrap and never crop. A trace line that spills past
    # 80 columns reads fine, but one that wraps onto a second row (with the
    # leading timestamp only on the first) reads as two different events - and
    # that is exactly what happens when stdout is a pipe, width=79.
    console.print(line, soft_wrap=True)


def sys_header() -> None:
    """One-time dump of the environment the demo is running in.

    Thinking: when a demo misbehaves on stage, the first question is always
    'whose machine and which terminal?'. Printing it once, greyed out, costs
    five lines and answers it. colour_system matters in particular: if it says
    'standard' your panels lose their accent colours entirely.
    """
    sys_log(
        "start",
        python=platform.python_version(),
        os=platform.system(),
        pid=os.getpid(),
        thread=threading.current_thread().name,
    )
    sys_log(
        "console",
        width=console.width,
        height=console.height,
        color_system=console.color_system,
        is_terminal=console.is_terminal,
    )
    sys_log("sys_log", enabled=SYS_LOG, hint="SYS_LOG=0 hides")


# ---------------------------------------------------------------------------
# Presentation helpers - no pub/sub knowledge lives in here.
# ---------------------------------------------------------------------------


def show_note(title: str, body: str, *, style: str = "cyan") -> None:
    """Render a small side-panel used to narrate what the classes are doing."""
    console.print(
        Panel(
            Text(body, style="dim"),
            title=f"[bold]{title}[/bold]",
            border_style=style,
            box=box.ROUNDED,
            expand=False,
            padding=(0, 1),
        )
    )


def show_state(publisher) -> None:
    """Draw the publisher's current internal state as a table.

    Thinking: this is the honest way to teach an object's state - instead of
    claiming 'the list grows' in a comment, print the list. Two subscribers
    means two rows, and the reader can check the claim.
    """
    table = Table(box=box.SIMPLE_HEAD, expand=False, border_style="bright_black")
    table.add_column("field", style="bold bright_black", no_wrap=True)
    table.add_column("value")

    table.add_row("subscribers", str(len(publisher.subscribers)))
    table.add_row("published", str(publisher.published))
    # Thinking: qsize() is a peek, not a sync point - with concurrent writers it
    # can be stale, with concurrent readers it can understate. For a demo that is
    # exactly right: we want a look at the box, not a lock on it.
    table.add_row("queued messages", str(publisher.message_queue.qsize()))
    table.add_row("deliveries", str(publisher.deliveries))

    names = ", ".join(s.name for s in publisher.subscribers) or "(nobody)"
    table.add_row("listening", names)

    console.print(
        Panel(
            table,
            title="[bold]publisher state[/bold]",
            border_style="bright_black",
            box=box.ROUNDED,
            expand=False,
        )
    )


# ---------------------------------------------------------------------------
# The pub/sub idea itself
# ---------------------------------------------------------------------------


class Publisher:
    """Holds the subscriber list and decides who hears a message.

    Thinking: a publisher is two things glued together - a registry (who wants
    my messages?) and a delivery rule (how do they get them?). A plain list is
    enough for the registry here; a dict keyed by name would only earn its keep
    once you need unsubscribe() or de-duplication.
    """

    def __init__(self, name: str = "publisher") -> None:
        self.name = name

        # Thinking: a Queue is thread-safe and FIFO. It is NOT the transport in
        # this file: publish() calls each subscriber directly and nothing ever
        # calls get() on this queue. So today it is an audit log - a record of
        # every message ever published. Replace the direct loop below with a
        # worker thread draining this queue and the demo becomes asynchronous,
        # which is the usual next step in a pub/sub lesson.
        self.message_queue: queue.Queue[str] = queue.Queue()

        # Thinking: a list preserves registration order, so delivery order is
        # the order in which subscribe() was called. That predictability is a
        # feature, not an accident - this file's output depends on it.
        self.subscribers: list["Subscriber"] = []

        # Counters the system channel reports. They exist so the grey lines can
        # show real numbers instead of guesses.
        self.published = 0
        self.deliveries = 0
        self.peak_queue_depth = 0

        sys_log(
            "Publisher.__init__",
            name=name,
            id=hex(id(self)),
            maxsize=self.message_queue.maxsize,
            subscribers=0,
        )

        show_note(
            "new Publisher",
            f"{self.name} created.\n"
            "No subscribers yet, empty queue. It has nobody to talk to.",
        )

    def subscribe(self, subscriber: "Subscriber") -> None:
        """Register a listener. Any object with .name and .receive() will do."""
        # Thinking: there is no runtime type check, only the annotation. Python
        # duck-types here, which is why a fake subscriber with one method is
        # easy to test - and also why a typo in receive() fails at publish time,
        # not at subscribe time.
        self.subscribers.append(subscriber)

        sys_log(
            "Publisher.subscribe",
            subscriber=subscriber.name,
            has_receive=callable(getattr(subscriber, "receive", None)),
            subscribers=len(self.subscribers),
        )

        show_note(
            "subscribe()",
            f"{subscriber.name} joined.\n"
            f"The subscriber list now holds {len(self.subscribers)} listener(s): "
            + ", ".join(s.name for s in self.subscribers),
            style="green",
        )

    def publish(self, message: str) -> None:
        """Record the message, then hand it to every subscriber in turn."""
        console.rule(f"[bold]{self.name}.publish()[/bold]", style="magenta")

        # Thinking: record first, deliver second. If a subscriber raised, the
        # queue would still hold the message, so the log stays the source of
        # truth even when delivery fails. The ordering is deliberate.
        t_put = time.perf_counter()
        self.message_queue.put(message)
        self.published += 1
        depth = self.message_queue.qsize()
        self.peak_queue_depth = max(self.peak_queue_depth, depth)

        sys_log(
            "Queue.put",
            msg=repr(escape(message)),
            bytes=len(message.encode("utf-8")),
            depth=depth,
            unfinished=self.message_queue.unfinished_tasks,
            ms=f"{(time.perf_counter() - t_put) * 1000:.3f}",
        )
        # Thinking: unfinished_tasks and depth are different questions - depth
        # is 'how many nobody has taken', unfinished is 'how many nobody has
        # task_done()'d'. They match here only because nobody consumes at all.
        sys_log(
            "dispatch.begin",
            mode="synchronous",
            targets=len(self.subscribers),
            thread=threading.current_thread().name,
            threads=threading.active_count(),
        )

        # Thinking: the meta line lives *inside* the panel rather than in
        # Panel(subtitle=...). A subtitle gets clipped to the panel's width,
        # which is fitted to the short message - body text widens it instead.
        body = Text.assemble(
            (message, "bold white"),
            (
                "\n" + f"#{self.published}  |  {len(self.subscribers)} listener(s)"
                f"  |  queue depth {depth}",
                "dim magenta",
            ),
        )
        console.print(
            Panel(
                body,
                title="[bold magenta]message[/bold magenta]",
                border_style="magenta",
                box=box.HEAVY,
                expand=False,
                padding=(0, 2),
            )
        )

        # Thinking: the loop below is the entire fan-out - that is the whole
        # trick. Because the call is synchronous, subscriber 2 does not see the
        # message until subscriber 1's receive() has returned, so one slow
        # listener stalls everyone queued behind it. Threaded delivery fixes the
        # stall and costs you the ordering guarantee.
        #
        # Thinking: iterate a snapshot, not the live list. A subscriber that
        # subscribed or unsubscribed *during* delivery would otherwise skip or
        # repeat listeners - list(...) turns that into a predictable no-op
        # instead of a mystery bug.
        t_dispatch = time.perf_counter()
        for index, subscriber in enumerate(list(self.subscribers), start=1):
            sys_log(
                "deliver.hand_off",
                to=subscriber.name,
                pos=f"{index}/{len(self.subscribers)}",
                depth=depth,
            )
            subscriber.receive(message)
            self.deliveries += 1

        sys_log(
            "dispatch.end",
            delivered=len(self.subscribers),
            ms=f"{(time.perf_counter() - t_dispatch) * 1000:.3f}",
            queue_depth=self.message_queue.qsize(),
        )

        show_state(self)


class Subscriber:
    """A listener. Stores its name and reacts to whatever lands in receive()."""

    def __init__(self, name: str, colour: str = "cyan") -> None:
        self.name = name
        # Thinking: colour is presentation only - the router never reads it.
        # Keeping it on the subscriber means the fan-out is readable by colour
        # without the delivery logic knowing anything about styling.
        self.colour = colour

        sys_log("Subscriber.__init__", name=name, id=hex(id(self)), colour=colour)

        show_note(
            "new Subscriber",
            f"{name} created.\n"
            "It knows how to receive, but no publisher knows about it yet.",
            style=colour,
        )

    def receive(self, message: str) -> None:
        """Called by the publisher, once per published message."""
        # Thinking: this method is the only thing a subscriber must implement. A
        # real one might write to a database, POST to a webhook or push onto a
        # websocket - the publisher would not change. That pluggability is why
        # pub/sub turns up everywhere.
        #
        # Note the message arrives bare: not who sent it, not when, not which
        # message number it is. Real systems wrap the payload in an envelope for
        # exactly this reason.
        t_enter = time.perf_counter()
        sys_log("Subscriber.receive", who=self.name, len=len(message))

        console.print(
            Panel(
                Text(message, style="white"),
                title=f"[bold]{self.name}[/bold] received",
                border_style=self.colour,
                box=box.ROUNDED,
                expand=False,
                padding=(0, 2),
            )
        )

        sys_log(
            "Subscriber.receive.end",
            who=self.name,
            ms=f"{(time.perf_counter() - t_enter) * 1000:.3f}",
        )


# ---------------------------------------------------------------------------
# The program: wire the pieces together
# ---------------------------------------------------------------------------

console.rule("[bold cyan]pub/sub demo[/bold cyan]", style="cyan")
sys_header()

show_note(
    "what happens next",
    "1. create one publisher\n"
    "2. create two subscribers\n"
    "3. register both with the publisher\n"
    "4. publish one message and watch it fan out\n"
    "5. publish a second one to show the registry is reusable",
)

# Thinking: order matters, and that ordering is the lesson - the publisher exists
# before anyone can subscribe to it, and subscribers must be registered before a
# message can reach them.
publisher = Publisher()

subscriber_1 = Subscriber("Subscriber 1", colour="cyan")
subscriber_2 = Subscriber("Subscriber 2", colour="yellow")

publisher.subscribe(subscriber_1)
publisher.subscribe(subscriber_2)

publisher.publish("Hello World")

# Thinking: a second publish proves the subscriptions persisted. It is easy to
# read the first fan-out as a one-shot and miss that the list is state.
publisher.publish("And hello again")

# Thinking: the closing summary is the only place that reports the consequence
# rather than the action - 2 published, 2 still queued, because nothing drains
# the queue. That mismatch is the whole 'this demo is synchronous' story.
console.rule("[bold cyan]done[/bold cyan]", style="cyan")
sys_log(
    "shutdown",
    published=publisher.published,
    deliveries=publisher.deliveries,
    depth=publisher.message_queue.qsize(),
    peak=publisher.peak_queue_depth,
    ms=f"{(time.perf_counter() - _BOOT) * 1000:.1f}",
)
console.print(
    f"[dim]{publisher.published} messages published, "
    f"{publisher.message_queue.qsize()} still sitting in the queue because "
    "nothing consumes it.[/dim]"
)
