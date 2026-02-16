# SharedObjects — Use Cases, Assessment, and Evolution

## The pattern

SharedObjects implements a specific pattern: **real-time bidirectional
synchronization of a tree-structured data store across WebSocket clients**.

```
Client A ──┐                    ┌── Client B (browser)
Client C ──┼── WebSocket ── Server ── SharedObject (Bag)
Device D ──┘    (push)          └── Client E (IoT device)

Every leaf change → instant broadcast to all subscribers
```

**Atomic unit**: a single leaf value (string, number, boolean, Bag subtree).
No merge, no conflict resolution. Last write wins on each leaf independently.
Path locking prevents concurrent edits on the same field at the UI level.

---

## Strengths

### 1. Unified data bus

The same mechanism serves browser-to-browser collaboration, server-to-client
push, and device-to-server communication. No separate systems for each
use case — one API, one protocol, one subscription model.

### 2. Zero-protocol devices

Any device that speaks WebSocket can participate. A Raspberry Pi, an ESP32,
a PLC gateway — they connect, subscribe, read/write leaves. No MQTT broker,
no REST polling, no message queue. The data model IS the protocol.

### 3. Tree structure maps to reality

Physical systems are naturally hierarchical:

```
factory/
  line1/
    press/
      temperature = 182.5
      pressure = 4.2
      status = "running"
    conveyor/
      speed = 1.5
      items_count = 4823
```

SharedObjects mirrors this structure directly. No ORM, no schema definition,
no serialization layer. The Bag IS the data model.

### 4. Built-in access control

Read/write tags are checked at subscription time. An operator can have
`write_tags='operator'` while a dashboard has `read_tags='viewer'`.
No separate authorization layer needed.

### 5. Persistence is transparent

Auto-save to XML or SQL happens without client awareness. A SharedObject
can survive server restarts, with optional versioned backups. The client
just subscribes — it doesn't know or care about persistence.

### 6. Expiration and lifecycle

SharedObjects auto-expire after the last subscriber disconnects. No manual
cleanup, no orphaned resources. The `expire` parameter controls how long
the object survives without subscribers (useful for reconnection grace
periods).

### 7. Path locking at field level

When user A focuses on a field, other users see it locked. This is
built into the subscription protocol, not an add-on. It prevents the
most common collaboration frustration (two people editing the same field)
without any developer effort.

---

## Weaknesses and limitations

### 1. No offline support

If a client disconnects, it misses all changes. On reconnection, it gets
the current state (full re-init), but intermediate changes are lost.
There is no change log, no replay, no delta sync.

**Impact**: Fine for real-time dashboards and control panels. Problematic
for mobile clients with intermittent connectivity.

**Mitigation**: For critical data, persistence + reload-on-connect is
already implemented. What's missing is client-side queuing of outgoing
changes during disconnection.

### 2. No change history

SharedObjects stores current state only. There is no audit trail, no
undo, no "who changed what and when". The Bag is a snapshot, not a journal.

**Impact**: Fine for operational data (sensor readings, control states).
Insufficient for regulated environments requiring audit trails.

**Mitigation**: `SharedLogger` exists as a subclass but is currently
a placeholder. A proper implementation would log changes to a persistent
store (SQL table with timestamp, user, path, old_value, new_value).

### 3. Full-tree init on subscribe

When a new client subscribes, it receives the entire SharedObject data.
For small objects (form data, device state) this is negligible. For large
objects (thousands of nodes), this becomes a bottleneck.

**Impact**: Limits practical SharedObject size. A factory with 500 sensors
updating every second could produce a large initial payload.

**Mitigation**: Subtree subscriptions — allow subscribing to a branch
(`factory.line1.press`) instead of the whole tree. This requires server-side
path filtering on subscribe and broadcast.

### 4. No rate limiting or throttling

Every leaf change triggers an immediate broadcast. A sensor updating
10 times per second generates 10 broadcasts per second to every subscriber.
No batching, no debounce, no sampling.

**Impact**: High-frequency sensors can saturate the WebSocket channel.
The `change_queue` in `SharedObjectsManager` was planned for batching
but never implemented.

**Mitigation**: Implement the `change_queue` consumer: batch changes
over a configurable window (e.g., 100ms), coalesce multiple updates to
the same path, send a single broadcast per batch. This is the single
most impactful improvement for IoT scenarios.

### 5. No guaranteed delivery

WebSocket is TCP (ordered, reliable) but the application layer doesn't
track delivery. If `broadcast()` fails for one client (disconnected socket,
full buffer), the change is silently lost for that client.

**Impact**: For UI collaboration, the client will resync on next user
action. For IoT control commands, a lost message could mean a missed
actuator command.

**Mitigation**: Add sequence numbers per shared object. Clients detect
gaps and request re-sync. This is how Phoenix Channels handles it.

### 6. Single-server architecture

SharedObjects live in the async server's memory. There is no replication,
no clustering, no multi-server support. All clients must connect to the
same server instance.

**Impact**: Limits horizontal scaling. Fine for single-site deployments
(which is Genro's typical use case). Blocking for multi-region or
high-availability requirements.

**Mitigation**: For multi-server, SharedObjects would need a shared
backing store (Redis pub/sub, PostgreSQL LISTEN/NOTIFY) to propagate
changes between server instances. This is a significant architectural
change and may not be worth the complexity for Genro's target market.

### 7. Broadcast is O(subscribers)

Every change is sent to every subscriber. There is no interest-based
filtering — if you subscribe to `factory`, you get changes to
`factory.line1.press.temperature` even if you only display `line2`.

**Impact**: Wastes bandwidth for large shared objects with many subscribers
interested in different subtrees.

**Mitigation**: Same as #3 — subtree subscriptions with server-side
path filtering.

---

## Intrinsic value of the pattern

SharedObjects implements what could be called a **real-time reactive
data tree**. This pattern is rare because most frameworks separate
the data model from the transport:

| Framework | Data model | Transport | Integration |
|-----------|-----------|-----------|-------------|
| Firebase Realtime DB | JSON tree | WebSocket | Tight (proprietary) |
| Meteor.js | MongoDB collections | DDP | Tight (Meteor-only) |
| Phoenix Presence | Flat map | Channels | Loose (presence only) |
| Django Channels | None built-in | WebSocket | None (DIY) |
| Genro SharedObjects | Bag tree | WebSocket | Native (Bag = UI = transport) |

The key insight is that Genro's Bag is simultaneously:

1. **The data model** — a tree with typed nodes and attributes
2. **The UI binding** — widgets bind to Bag paths, auto-update on change
3. **The network protocol** — changes are Bag paths + values, serialized as XML
4. **The persistence format** — saved as XML or SQL, loaded back as Bag

This unification eliminates entire categories of glue code. There is no
serialization step, no data mapping, no event bus wiring. A change to a
Bag leaf in one client's memory travels to the server, is applied to the
shared Bag, broadcast to other clients, applied to their Bags, and
triggers UI updates — all through the same Bag subscription mechanism.

**No other open-source web framework offers this level of integration.**

Firebase comes closest but is proprietary, cloud-only, and doesn't
integrate with the UI layer. Meteor had a similar vision but was
MongoDB-specific and is effectively abandoned. Phoenix LiveView
renders server-side HTML, not a synchronized data tree.

---

## Use case scenarios

### 1. IoT and robotics

**Demonstrated**: Robotic arm at PyCon Italy. Raspberry Pi with WebSocket
client connected to Genro server. SharedObject with motor angles as leaves.
Browser sliders set desired angles; encoders report actual angles back.
Bidirectional, real-time, zero protocol overhead.

**Extended**:

- **Sensors** (input): temperature, humidity, pressure, light, CO2 — any
  measurable quantity written as a leaf. Dashboards subscribe and display.
  Threshold-based alerts trigger when a value crosses a limit.

- **Actuators** (output): relays, valves, motors, servos — controlled by
  writing to leaves from a browser UI. The device reads the new value
  and acts. Feedback (actual state) flows back as a leaf update.

- **Mixed**: A greenhouse with temperature sensors (input), irrigation
  valves (output), and a dashboard showing both. One SharedObject,
  one subscription, bidirectional.

**Strengths for this scenario**: Zero-protocol devices, tree-maps-to-reality,
built-in access control (operator vs viewer).

**Weaknesses**: No rate limiting (high-frequency sensors), no guaranteed
delivery (critical actuator commands), no offline queuing (intermittent
connectivity).

### 2. Industry 4.0

**Digital twin**: A SharedObject IS the digital twin of a machine.
Every operational parameter is a leaf: temperature, pressure, RPM,
cycle time, part count, alarm state. The physical machine and its
digital representation are synchronized in real time.

```
machine_twin/
  status = "running"
  cycle_time = 12.3
  parts/
    produced = 4823
    rejected = 17
  alarms/
    over_temperature = false
    low_pressure = true
  setpoints/
    target_temperature = 180
    target_pressure = 4.5
```

**SCADA replacement**: For small/medium installations, a Genro page with
SharedObjects replaces proprietary SCADA software. Browser-based (no
client installation), accessible from any device, real-time updates.

**OEE dashboard**: Overall Equipment Effectiveness calculated from
SharedObject data. Availability, performance, and quality metrics
update in real time as machines report status changes.

**Alarm management**: An alarm is a leaf change (`alarm.press3 = "over_temp"`).
All operator screens see it instantly. Acknowledgment is a leaf write
(`alarm.press3.ack = true`). The alarm history needs the change log
improvement (weakness #2) to be complete.

**Strengths for this scenario**: Digital twin as data tree, unified
supervision + control, zero-install client.

**Weaknesses**: Single-server limits factory scale, no change history
for regulatory compliance, no guaranteed delivery for safety-critical
commands. Safety-critical control should always have a separate,
certified system — SharedObjects is for supervision and non-critical
control.

### 3. Remote education

**Classroom monitoring**: Each student works on exercises in their own
SharedObject. The teacher subscribes to all student SharedObjects and
sees, in real time:

- Who is working, who is idle
- What each student is writing/answering
- Who is stuck (no changes for N seconds)
- Errors or wrong approaches as they happen

**Live intervention**: The teacher writes to a student's SharedObject
to correct an error, highlight a field, or send a hint. The student
sees the change instantly. No separate chat, no screen sharing — the
data model IS the communication channel.

**Shared exercise**: A single SharedObject with the exercise data.
All students see the same problem. The teacher modifies a parameter
and everyone's view updates. Good for "what-if" demonstrations.

**Code review**: Teacher and student see the same code (SharedObject
with source text as leaf). Teacher selects a line (path locking shows
where the teacher is looking), adds a comment (leaf write). Real-time
pair review.

**Strengths for this scenario**: Teacher sees all students without
polling, intervention is instant and in-context, path locking shows
who is editing what.

**Weaknesses**: Full-tree init on subscribe (teacher subscribing to
30 students gets 30 full payloads), no change history (teacher can't
review what a student did while not watching).

### 4. Collaborative operations

**Shared dashboard**: Operations team viewing the same data. Filters
applied by one operator are visible to all (or private — access control
decides). Annotations, notes, flags are shared in real time.

**Workflow state**: A process moves through states (submitted → approved
→ in_progress → completed). Each state change is a leaf update visible
to all stakeholders instantly. No polling, no email notifications for
state changes.

**Booking/reservation**: Available slots as leaves. When a slot is booked,
the leaf changes and all clients see it instantly. Path locking prevents
double-booking (while user A is booking slot X, user B sees it locked).

### 5. Real-time monitoring

**CI/CD wall display**: Build status, test results, deployment state as
SharedObject leaves. Team sees the wall update in real time. No polling
Jenkins, no refreshing GitHub Actions.

**Server monitoring**: CPU, memory, disk usage written by agents on each
server. A central dashboard subscribes to all server SharedObjects.
Alerts on threshold crossing.

**Live trading / financial data**: Order book, quotes, positions as
leaves. Multiple traders see the same data. Each trader's actions are
instantly visible to others and to the risk manager.

**Strengths for this scenario**: Multiple observers with zero polling,
tree structure maps to entity hierarchy, access control per role.

**Weaknesses**: No rate limiting for high-frequency data, single-server
limits the number of concurrent observers.

### 6. Kiosk and digital signage

**Museum/exhibit**: Content panels (text, images, media URLs) as
SharedObject leaves. A curator changes content from an admin page;
all kiosks update instantly. No CMS publish cycle, no panel restart.

**Corporate dashboards**: KPIs, announcements, alerts on lobby screens.
Updated from a management page, displayed on any number of screens.

**Event displays**: Conference schedule, room assignments, speaker info.
Changes propagate to all displays in real time. Last-minute room changes
are instantly visible everywhere.

**Strengths for this scenario**: Zero-install displays (browser in
fullscreen), instant updates, one-to-many broadcast.

**Weaknesses**: None significant for this use case. SharedObjects is
a natural fit.

---

## Improvement roadmap

Priority-ordered improvements based on the analysis above:

### Priority 1 — Change batching (impact: high, effort: medium)

Implement the planned `change_queue` consumer in `SharedObjectsManager`.
Batch changes over a configurable window (50-200ms), coalesce multiple
updates to the same path within the window, broadcast once per batch.

Enables high-frequency IoT without saturating WebSocket channels.

### Priority 2 — Subtree subscriptions (impact: high, effort: medium)

Allow `subscribe(shared_id, path='factory.line1')` to receive only
changes under that path. Requires path prefix filtering in `broadcast()`.

Reduces bandwidth for large shared objects and enables the education
scenario (teacher subscribes to 30 subtrees instead of 30 full objects).

### Priority 3 — Change log (impact: medium, effort: medium)

Log changes to a ring buffer or SQL table: `{timestamp, user, path,
old_value, new_value}`. Enable replay for audit, undo, and "catch up
after reconnect".

Required for Industry 4.0 compliance and education review.

### Priority 4 — Sequence numbers (impact: medium, effort: low)

Add a monotonic sequence number to each shared object. Include it in
every broadcast. Clients detect gaps and request full re-sync.

Converts "silent data loss" to "detected and recovered".

### Priority 5 — Client-side outgoing queue (impact: medium, effort: low)

Buffer outgoing changes during WebSocket disconnection. Replay on
reconnect. The `ReconnectingWebSocket` already queues messages
(`maxEnqueuedMessages`), but SharedObject changes need ordering
guarantees.

Enables intermittent connectivity scenarios (mobile, unstable networks).

### Priority 6 — Broadcast error handling (impact: low, effort: low)

Fix the known issue #4: check for `None` channel before `write_message()`.
Unsubscribe crashed clients automatically. Log the cleanup.

---

## Comparison with alternatives

| Feature | SharedObjects | Firebase RT | Meteor DDP | MQTT + Dashboard |
|---------|--------------|-------------|------------|-----------------|
| Data model | Bag tree | JSON tree | MongoDB docs | Topic + payload |
| UI binding | Native (Bag paths) | SDK-specific | Blaze/React | Separate |
| Access control | Built-in (tags) | Rules engine | Publications | Broker ACL |
| Offline support | None | Yes | Yes (Minimongo) | QoS levels |
| Persistence | XML/SQL | Cloud | MongoDB | Broker + DB |
| Self-hosted | Yes | No | Yes | Yes |
| Rate limiting | None | Automatic | None | Broker config |
| Change history | None | None (paid) | Oplog | Broker retain |
| Path locking | Built-in | None | None | None |
| Tree structure | Native | Native | No (flat docs) | No (flat topics) |
| License | Open source | Proprietary | MIT (dead) | Various |
| Setup complexity | Zero (built-in) | Account + SDK | Full stack | Broker + clients + dashboard |

**SharedObjects' unique position**: the only self-hosted, open-source
solution that unifies data model, UI binding, transport, and persistence
in a single mechanism, with built-in access control and path locking.
Its limitations (no offline, no batching, single-server) are addressable
with focused improvements that don't require architectural changes.
