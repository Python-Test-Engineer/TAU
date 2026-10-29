# pub_sub_simple.py — teaching notes

A 99-line publish/subscribe demo where every step prints itself. Use this page
alongside `pub_sub_simple.py`; nothing here is needed to run the file.

Source: `C:\Users\mrcra\Desktop\TAU\pub_sub_simple.py`
Plain twin with colour panels and a grey system trace: `pub_sub.py`

---

## Run it

    cd C:\Users\mrcra\Desktop\TAU
    uv run python pub_sub_simple.py

No dependencies beyond the standard library (`queue`). Output is ten numbered
steps; the whole run takes milliseconds.

---

## The idea in one sentence

**A publisher keeps a list of listeners and, on every message, calls each
listener's `receive()` in turn.**

That is the entire implementation. Everything else in the file is printing, and
everything else in real systems — brokers, topics, retries, queues — is that
sentence with durability and distribution bolted on.

---

## The output, annotated

Real output from the current file. The `# <-` comments are mine, not the
program's:

    [1] program start
    [2] Publisher.__init__()  building the object
        - queue.Queue created     maxsize=0                    # unbounded
        - subscriber list created len=0  []                    # nobody listening yet
    [3] Subscriber.__init__(Subscriber 1)
        - knows how to receive(), no publisher knows about it yet
    [4] Subscriber.__init__(Subscriber 2)
        - knows how to receive(), no publisher knows about it yet
    [5] Publisher.subscribe(Subscriber 1)
        - before append  subscribers=[]                        # the mutation,
        - after append   subscribers=['Subscriber 1']          # shown from both sides
    [6] Publisher.subscribe(Subscriber 2)
        - before append  subscribers=['Subscriber 1']
        - after append   subscribers=['Subscriber 1', 'Subscriber 2']
    [7] Publisher.publish('Hello World')
        - queue.put() done        queue size=1                 # recorded...
        - looping over 2 subscriber(s)
        - hand-off 1/2 -> Subscriber 1
    [8] Subscriber.receive() -> Subscriber 1
        <- Subscriber 1 received message: Hello World
        - hand-off 2/2 -> Subscriber 2
    [9] Subscriber.receive() -> Subscriber 2
        <- Subscriber 2 received message: Hello World
        - loop finished           queue size=1  (unchanged: nothing calls get())
    [10] program end
        - publisher published 1 message, queue still holds 1

Two conventions in the trace, worth stating once so students can read it:

| prefix | meaning |
| --- | --- |
| `[n]` | a numbered step: something entered a method |
| `- ` | a fact about the step above (a value, a size, a count) |
| `<- ` | an inbound event: a subscriber was actually called |

---

## Reading the code

### 1. The step counter (lines 11–22)

    import queue
    _step = 0

    def step(text):
        global _step
        _step += 1
        print(f"[{_step}] {text}")

`_step` lives at module level, not on a class, because it describes *the run*,
not the system. If it were `Publisher.step_count` you would have to decide which
object owns the counter — and the answer is "none of them", which is the point.

The `global` keyword is the price of a module-level counter. Show students the
alternative (`itertools.count()`) only if someone asks; the explicit version
teaches more at this stage.

### 2. `Publisher` (lines 25–63)

`__init__` creates exactly two pieces of state:

| attribute | type | role |
| --- | --- | --- |
| `message_queue` | `queue.Queue` | records every message published |
| `subscribers` | `list` | who to call on each publish |

`subscribe()` is one line of real work — `self.subscribers.append(subscriber)` —
flanked by two prints that show the list before and after. That is deliberate:
"subscribing" sounds like a system, and students should see it is an `append`.

`publish()` is where the two ideas meet:

    self.message_queue.put(message)          # 1. record it
    print(...queue size...)                  #    report the queue
    for position, subscriber in enumerate(self.subscribers, start=1):
        print(...hand-off...)                # 2. show who is next
        subscriber.receive(message)          #    hand it over
    print(...loop finished...)                # 3. close the bracket

The queue print sits before the loop and the "loop finished" print after it, so
the trace brackets the fan-out: loop start, both hand-offs (each immediately
followed by the `receive()` step it caused), loop end.

**The `queue` is not the delivery mechanism.** Nothing in this file calls
`get()`. `publish()` calls subscribers directly; the queue only accumulates
messages. Say this out loud when teaching: the queue *looks* like a transport
and is not one. Its size goes up by one per publish and never comes down, which
the last print in `publish()` and step `[10]` both show.

### 3. `Subscriber` (lines 66–75)

    def __init__(self, name):
        self.name = name

    def receive(self, message):
        step(f"Subscriber.receive() -> {self.name}")
        print(f"    <- {self.name} received message: {message}")

`receive()` is the only thing a subscriber *must* implement. There is no base
class, no interface, no `isinstance` check — Python only discovers a mismatch
when the attribute is actually used. Worth demonstrating live, and the two
failures land in different places:

    publisher.subscribe(object())
    # AttributeError: 'object' object has no attribute 'name'
    # ...and it fails here, inside subscribe(), not at publish

    class Bare:
        name = "Bare"

    publisher.subscribe(Bare())     # accepted: the trace only needs .name
    publisher.publish("boom")
    # AttributeError: 'Bare' object has no attribute 'receive'
    # ...fails mid fan-out, after the message was already queued

Note *why* the first one fails early: the tracing line
`step(f"Publisher.subscribe({subscriber.name})")` touches `.name`, so the print
does the type checking Python does not. Strip the prints (the 34-line original)
and a plain `object()` subscribes happily and only breaks on publish. Good
reminder that logging is code and has access to the objects it describes.

### 4. The program (lines 78–99)

Five statements, in an order that matters:

    publisher = Publisher()                  # the hub exists first
    subscriber_1 = Subscriber("Subscriber 1")  # then the listeners
    subscriber_2 = Subscriber("Subscriber 2")
    publisher.subscribe(subscriber_1)        # then they register
    publisher.subscribe(subscriber_2)
    publisher.publish("Hello World")         # only now can a message reach anyone

Swap the last two lines and the message goes nowhere while the trace still shows
a successful publish — a good first exercise (see below).

---

## Four claims the trace lets you prove

Do not assert these; point at the output.

1. **Two subscribers means two calls.** `hand-off 1/2`, `hand-off 2/2`, two
   `receive()` steps. Add a third subscriber and the count follows.
2. **Delivery order is registration order.** The list is a `list`, the loop is a
   `for`, so Subscriber 1 is always called before Subscriber 2.
3. **Delivery is synchronous.** Steps `[8]` and `[9]` happen *inside* step `[7]`.
   The `[7]` block does not finish until both `receive()` calls return. A slow
   listener therefore stalls every listener behind it — and the publisher.
4. **The message carries nothing but itself.** `receive(message)` gets a string:
   no sender, no timestamp, no message id. Real systems wrap payloads in an
   envelope precisely because subscribers eventually need that context.

---

## Talking points for the class

- Where does the "system" live in these 99 lines? (Answer: in `self.subscribers`
  and the `for` loop. Two lines.)
- Why does `Publisher` hold a *list* rather than a *set*? (Order is observable
  behaviour here. A set would let delivery order vary.)
- Who decides what happens on a message — the publisher or the subscriber?
  (The subscriber: the publisher only knows how to call `receive`.)
- If `print` is our logger, what breaks when this becomes a real service? (Two
  processes cannot share a list; you need a network boundary, retries, and a
  drain loop on that queue.)
- What is the queue *for*, then? (Nothing yet. It is a record. The next version
  of this demo gives it a consumer thread.)

---

## Exercises

Ordered by size of the change.

1. **Add a third subscriber.** Predict the trace before running: how many
   `hand-off` lines, what does `len` say in step `[7]`?
2. **Publish before subscribing.** Move `publish("Hello World")` above the two
   `subscribe()` calls. The publish still succeeds and prints `looping over 0
   subscriber(s)`. Message sent, nobody heard — the defining failure mode of
   pub/sub.
3. **Make a listener slow.** Add `time.sleep(1)` at the top of `receive()`.
   Watch the whole run take two seconds and observe that Subscriber 2 hears
   nothing until Subscriber 1 finishes.
4. **Break the contract.** `publisher.subscribe(object())` fails *immediately*
   (AttributeError: `name`) because the trace print touches `.name`. Then try a
   class with `name = "Bare"` and no `receive`: it subscribes fine and fails
   during the fan-out, after `queue.put()` already ran. Two failures, two very
   different places.
5. **Add `unsubscribe()`.** One method, one `list.remove`. Then ask: what happens
   if a subscriber unsubscribes *during* the delivery loop? It is worse than it
   looks: the `for` is walking the live list by position, so removing the next
   listener shifts it down and it is silently skipped — the trace shows
   `hand-off 1/2` and then the loop simply ends. (Verified by running it.) The rich version iterates a snapshot,
   `list(self.subscribers)`, so the same trick removes the listener only after
   the current fan-out finishes.
6. **Give the queue a consumer.** Start a thread that loops on
   `publisher.message_queue.get()`, calls `receive`, then `task_done()`. Now the
   queue is a transport, delivery is asynchronous, and the "queue size" print
   stops growing. This is the jump from a demo to a system.

---

## What this demo deliberately leaves out

Say these out loud too, so students know the shape of the missing pieces:

- no unsubscribe, no wildcard topics, no filtering
- no envelope (sender, timestamp, id, content type)
- no durability: the in-memory queue dies with the process
- no error handling: one raising subscriber aborts the whole fan-out
- no threading or async: see exercise 6
- no backpressure: `maxsize=0` means `put()` never blocks
- `print` as logging: no levels, no timestamps, no destination control

---

## Next steps

- `pub_sub.py` — identical logic, with rich panels for the application view and a
  greyed-out `sys` trace (`SYS_LOG=0` hides it) showing queue depth, object ids,
  thread name and per-delivery timings. Good for a projector; the simple file is
  better for reading code.
- Exercise 6 is the real lesson: move delivery onto a worker thread and the queue
  stops being decoration.
