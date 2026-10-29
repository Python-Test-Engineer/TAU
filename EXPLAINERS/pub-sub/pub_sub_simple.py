"""pub_sub_simple.py - pub/sub with a print() at every point it does something.

This is the plain twin of pub_sub.py: same two classes, same behaviour, no rich,
no colour, no panels. Everything you would want to see is a boring print line,
so nothing on screen looks like magic.

Reading the output: every line starts with a bracketed counter, bumped by step().
Lines indented with "-" or "<-" are details belonging to the step above them.
"""

import queue

# Counter for the step numbers in the output. Deliberately a module-level
# variable, not state on a class: it describes the *run*, not the system.
_step = 0


def step(text):
    """Print the next numbered step. This is the only 'logging' in the file."""
    global _step
    _step += 1
    print(f"[{_step}] {text}")


class Publisher:
    def __init__(self):
        step("Publisher.__init__()  building the object")

        self.message_queue = queue.Queue()
        # maxsize=0 means unbounded, i.e. put() never blocks.
        print(f"    - queue.Queue created     maxsize={self.message_queue.maxsize}")

        self.subscribers = []
        print(f"    - subscriber list created len={len(self.subscribers)}  {self.subscribers}")

    def subscribe(self, subscriber):
        step(f"Publisher.subscribe({subscriber.name})")

        # Print both sides of the mutation: it is the cheapest way to show that
        # appending is the whole of 'subscribing'.
        print(f"    - before append  subscribers={[s.name for s in self.subscribers]}")
        self.subscribers.append(subscriber)
        print(f"    - after append   subscribers={[s.name for s in self.subscribers]}")

    def publish(self, message):
        step(f"Publisher.publish({message!r})")

        self.message_queue.put(message)
        print(f"    - queue.put() done        queue size={self.message_queue.qsize()}")

        # This loop is the entire fan-out: one message in, one receive() call
        # per subscriber, in the order they subscribed.
        print(f"    - looping over {len(self.subscribers)} subscriber(s)")
        for position, subscriber in enumerate(self.subscribers, start=1):
            print(f"    - hand-off {position}/{len(self.subscribers)} -> {subscriber.name}")
            subscriber.receive(message)

        # The queue is a record, not a transport: nothing ever calls get(), so
        # it grows by one per publish and never shrinks.
        print(
            f"    - loop finished           queue size={self.message_queue.qsize()}"
            f"  (unchanged: nothing calls get())"
        )


class Subscriber:
    def __init__(self, name):
        self.name = name
        step(f"Subscriber.__init__({name})")
        print("    - knows how to receive(), no publisher knows about it yet")

    def receive(self, message):
        # Reached only because a publisher called us; it has no other trigger.
        step(f"Subscriber.receive() -> {self.name}")
        print(f"    <- {self.name} received message: {message}")


# ---------------------------------------------------------------------------
# The program. Each line here is one step in the output, so the trace and the
# script read in the same order.
# ---------------------------------------------------------------------------

step("program start")

publisher = Publisher()

subscriber_1 = Subscriber("Subscriber 1")
subscriber_2 = Subscriber("Subscriber 2")

publisher.subscribe(subscriber_1)
publisher.subscribe(subscriber_2)

publisher.publish("Hello World")

step("program end")
print(
    f"    - publisher published 1 message, "
    f"queue still holds {publisher.message_queue.qsize()}"
)
