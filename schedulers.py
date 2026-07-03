"""
CPU Scheduling Algorithms — pure logic, no UI code.

Every scheduler function takes a list of process dicts:
    {"pid": "P1", "arrival": 0, "burst": 5, "priority": 2}
and a tie-break rule of "lowest pid wins ties" throughout.

Each scheduler returns a dict:
    {
        "timeline": [ {"pid": "P1", "start": 0, "end": 4}, ... ],   # includes "IDLE" slices
        "log": [ {"time": 0, "message": "..."}, ... ],
        "metrics": { "P1": {"waiting": 0, "turnaround": 4, "completion": 4,
                             "response": 0, "arrival": 0, "burst": 4}, ... },
        "averages": {"waiting": .., "turnaround": .., "response": ..,
                     "cpu_utilization": .., "context_switches": ..}
    }

Priority convention used throughout: LOWER priority number = HIGHER priority
(this is the common textbook convention; it is stated in the UI log too).
"""


def _pid_key(p):
    """Sort helper: numeric part of PID if possible, else the string itself."""
    pid = p["pid"]
    digits = "".join(ch for ch in pid if ch.isdigit())
    return (int(digits) if digits else 0, pid)


def _init_metrics(processes):
    metrics = {}
    for p in processes:
        metrics[p["pid"]] = {
            "arrival": p["arrival"],
            "burst": p["burst"],
            "waiting": 0,
            "turnaround": 0,
            "completion": 0,
            "response": None,
        }
    return metrics


def _finalize(processes, timeline, log, metrics):
    total_time = timeline[-1]["end"] if timeline else 0
    busy_time = sum(s["end"] - s["start"] for s in timeline if s["pid"] != "IDLE")
    context_switches = 0
    last_pid = None
    for s in timeline:
        if s["pid"] != "IDLE" and s["pid"] != last_pid:
            if last_pid is not None:
                context_switches += 1
            last_pid = s["pid"]

    n = len(processes)
    avg_wait = sum(m["waiting"] for m in metrics.values()) / n if n else 0
    avg_turn = sum(m["turnaround"] for m in metrics.values()) / n if n else 0
    avg_resp = sum(m["response"] for m in metrics.values()) / n if n else 0
    utilization = (busy_time / total_time * 100) if total_time else 0

    return {
        "timeline": timeline,
        "log": log,
        "metrics": metrics,
        "averages": {
            "waiting": round(avg_wait, 2),
            "turnaround": round(avg_turn, 2),
            "response": round(avg_resp, 2),
            "cpu_utilization": round(utilization, 2),
            "context_switches": context_switches,
        },
    }


def _add_idle_if_needed(timeline, log, current_time, next_time):
    if next_time > current_time:
        timeline.append({"pid": "IDLE", "start": current_time, "end": next_time})
        log.append({"time": current_time, "message": f"CPU idle, no process ready until t={next_time}"})
    return next_time


# ---------------------------------------------------------------------------
# Non-preemptive family: FCFS, SJF, Priority (NPP)
# All three share the same shape: repeatedly pick one process to run to
# completion from whatever has arrived so far.
# ---------------------------------------------------------------------------

def _run_non_preemptive(processes, select_fn, describe_fn):
    remaining = sorted(processes, key=lambda p: (p["arrival"], _pid_key(p)))
    metrics = _init_metrics(processes)
    timeline = []
    log = []
    time = 0
    done = set()

    while len(done) < len(processes):
        ready = [p for p in remaining if p["pid"] not in done and p["arrival"] <= time]
        if not ready:
            next_arrival = min(p["arrival"] for p in remaining if p["pid"] not in done)
            time = _add_idle_if_needed(timeline, log, time, next_arrival)
            continue

        chosen = select_fn(ready)
        start = time
        end = start + chosen["burst"]

        log.append({"time": start, "message": describe_fn(chosen, ready, start)})

        metrics[chosen["pid"]]["response"] = start - chosen["arrival"]
        metrics[chosen["pid"]]["completion"] = end
        metrics[chosen["pid"]]["turnaround"] = end - chosen["arrival"]
        metrics[chosen["pid"]]["waiting"] = start - chosen["arrival"]

        timeline.append({"pid": chosen["pid"], "start": start, "end": end})
        done.add(chosen["pid"])
        time = end

    return _finalize(processes, timeline, log, metrics)


def fcfs(processes, **kwargs):
    def select(ready):
        return min(ready, key=lambda p: (p["arrival"], _pid_key(p)))

    def describe(chosen, ready, t):
        return f"{chosen['pid']} arrived earliest among ready processes → dispatch (burst={chosen['burst']})"

    return _run_non_preemptive(processes, select, describe)


def sjf(processes, **kwargs):
    def select(ready):
        return min(ready, key=lambda p: (p["burst"], p["arrival"], _pid_key(p)))

    def describe(chosen, ready, t):
        others = ", ".join(f"{p['pid']}={p['burst']}" for p in ready if p["pid"] != chosen["pid"])
        extra = f" (others ready: {others})" if others else ""
        return f"{chosen['pid']} has shortest burst ({chosen['burst']}) among ready processes → dispatch{extra}"

    return _run_non_preemptive(processes, select, describe)


def priority_npp(processes, **kwargs):
    def select(ready):
        return min(ready, key=lambda p: (p["priority"], p["arrival"], _pid_key(p)))

    def describe(chosen, ready, t):
        return f"{chosen['pid']} has highest priority (value={chosen['priority']}, lower=higher) among ready → dispatch"

    return _run_non_preemptive(processes, select, describe)


# ---------------------------------------------------------------------------
# Preemptive family: SRTF, Priority (PP), Round Robin
# All three use a time-stepped simulation loop, advancing one unit at a time.
# ---------------------------------------------------------------------------

def srtf(processes, **kwargs):
    procs = {p["pid"]: dict(p, remaining=p["burst"]) for p in processes}
    metrics = _init_metrics(processes)
    timeline = []
    log = []
    time = 0
    completed = 0
    n = len(processes)
    running_pid = None
    slice_start = None

    while completed < n:
        ready = [p for p in procs.values() if p["remaining"] > 0 and p["arrival"] <= time]
        if not ready:
            if running_pid is not None:
                timeline.append({"pid": running_pid, "start": slice_start, "end": time})
                running_pid = None
            next_arrival = min(p["arrival"] for p in procs.values() if p["remaining"] > 0)
            time = _add_idle_if_needed(timeline, log, time, next_arrival)
            continue

        chosen = min(ready, key=lambda p: (p["remaining"], p["arrival"], _pid_key(p)))

        if metrics[chosen["pid"]]["response"] is None:
            metrics[chosen["pid"]]["response"] = time - chosen["arrival"]

        if chosen["pid"] != running_pid:
            if running_pid is not None:
                timeline.append({"pid": running_pid, "start": slice_start, "end": time})
                prev_remaining = procs[running_pid]["remaining"]
                log.append({
                    "time": time,
                    "message": f"{chosen['pid']} (remaining={chosen['remaining']}) < {running_pid} "
                               f"(remaining={prev_remaining}) → PREEMPT {running_pid}, dispatch {chosen['pid']}",
                })
            else:
                log.append({"time": time, "message": f"{chosen['pid']} has shortest remaining time ({chosen['remaining']}) → dispatch"})
            running_pid = chosen["pid"]
            slice_start = time

        chosen["remaining"] -= 1
        time += 1

        if chosen["remaining"] == 0:
            timeline.append({"pid": chosen["pid"], "start": slice_start, "end": time})
            running_pid = None
            metrics[chosen["pid"]]["completion"] = time
            metrics[chosen["pid"]]["turnaround"] = time - chosen["arrival"]
            metrics[chosen["pid"]]["waiting"] = metrics[chosen["pid"]]["turnaround"] - chosen["burst"]
            log.append({"time": time, "message": f"{chosen['pid']} completes"})
            completed += 1

    timeline = _merge_adjacent(timeline)
    return _finalize(processes, timeline, log, metrics)


def priority_pp(processes, **kwargs):
    procs = {p["pid"]: dict(p, remaining=p["burst"]) for p in processes}
    metrics = _init_metrics(processes)
    timeline = []
    log = []
    time = 0
    completed = 0
    n = len(processes)
    running_pid = None
    slice_start = None

    while completed < n:
        ready = [p for p in procs.values() if p["remaining"] > 0 and p["arrival"] <= time]
        if not ready:
            if running_pid is not None:
                timeline.append({"pid": running_pid, "start": slice_start, "end": time})
                running_pid = None
            next_arrival = min(p["arrival"] for p in procs.values() if p["remaining"] > 0)
            time = _add_idle_if_needed(timeline, log, time, next_arrival)
            continue

        chosen = min(ready, key=lambda p: (p["priority"], p["arrival"], _pid_key(p)))

        if metrics[chosen["pid"]]["response"] is None:
            metrics[chosen["pid"]]["response"] = time - chosen["arrival"]

        if chosen["pid"] != running_pid:
            if running_pid is not None:
                timeline.append({"pid": running_pid, "start": slice_start, "end": time})
                prev_priority = procs[running_pid]["priority"]
                log.append({
                    "time": time,
                    "message": f"{chosen['pid']} (priority={chosen['priority']}) higher than {running_pid} "
                               f"(priority={prev_priority}) → PREEMPT {running_pid}, dispatch {chosen['pid']}",
                })
            else:
                log.append({"time": time, "message": f"{chosen['pid']} has highest priority ({chosen['priority']}) → dispatch"})
            running_pid = chosen["pid"]
            slice_start = time

        chosen["remaining"] -= 1
        time += 1

        if chosen["remaining"] == 0:
            timeline.append({"pid": chosen["pid"], "start": slice_start, "end": time})
            running_pid = None
            metrics[chosen["pid"]]["completion"] = time
            metrics[chosen["pid"]]["turnaround"] = time - chosen["arrival"]
            metrics[chosen["pid"]]["waiting"] = metrics[chosen["pid"]]["turnaround"] - chosen["burst"]
            log.append({"time": time, "message": f"{chosen['pid']} completes"})
            completed += 1

    timeline = _merge_adjacent(timeline)
    return _finalize(processes, timeline, log, metrics)


def round_robin(processes, quantum=2, **kwargs):
    quantum = int(quantum) if quantum else 2
    procs = {p["pid"]: dict(p, remaining=p["burst"]) for p in processes}
    metrics = _init_metrics(processes)
    timeline = []
    log = []
    time = 0
    n = len(processes)
    completed = 0

    arrivals_sorted = sorted(processes, key=lambda p: (p["arrival"], _pid_key(p)))
    arrival_idx = 0
    queue = []

    # enqueue any processes that arrive at time 0
    while arrival_idx < n and arrivals_sorted[arrival_idx]["arrival"] <= time:
        queue.append(arrivals_sorted[arrival_idx]["pid"])
        arrival_idx += 1

    if not queue and arrival_idx < n:
        time = arrivals_sorted[arrival_idx]["arrival"]
        while arrival_idx < n and arrivals_sorted[arrival_idx]["arrival"] <= time:
            queue.append(arrivals_sorted[arrival_idx]["pid"])
            arrival_idx += 1

    while completed < n:
        if not queue:
            if arrival_idx < n:
                next_arrival = arrivals_sorted[arrival_idx]["arrival"]
                time = _add_idle_if_needed(timeline, log, time, next_arrival)
                while arrival_idx < n and arrivals_sorted[arrival_idx]["arrival"] <= time:
                    queue.append(arrivals_sorted[arrival_idx]["pid"])
                    arrival_idx += 1
            continue

        pid = queue.pop(0)
        p = procs[pid]
        start = time
        run_for = min(quantum, p["remaining"])
        end = start + run_for

        if metrics[pid]["response"] is None:
            metrics[pid]["response"] = start - p["arrival"]

        timeline.append({"pid": pid, "start": start, "end": end})
        log.append({
            "time": start,
            "message": f"{pid} runs for {run_for} unit(s) (quantum={quantum}, remaining before={p['remaining']})",
        })

        p["remaining"] -= run_for
        time = end

        # Convention: processes that arrive DURING this slice are enqueued
        # BEFORE the just-run process is re-queued (if it still has work).
        while arrival_idx < n and arrivals_sorted[arrival_idx]["arrival"] <= time:
            newly = arrivals_sorted[arrival_idx]["pid"]
            queue.append(newly)
            log.append({"time": time, "message": f"{newly} arrives → enqueued"})
            arrival_idx += 1

        if p["remaining"] > 0:
            queue.append(pid)
            log.append({"time": time, "message": f"{pid} quantum expired, {p['remaining']} remaining → re-enqueued"})
        else:
            metrics[pid]["completion"] = time
            metrics[pid]["turnaround"] = time - p["arrival"]
            metrics[pid]["waiting"] = metrics[pid]["turnaround"] - p["burst"]
            log.append({"time": time, "message": f"{pid} completes"})
            completed += 1

    timeline = _merge_adjacent(timeline)
    return _finalize(processes, timeline, log, metrics)


def _merge_adjacent(timeline):
    """Merge back-to-back slices of the same pid (cosmetic clean-up for Gantt chart)."""
    if not timeline:
        return timeline
    merged = [dict(timeline[0])]
    for s in timeline[1:]:
        if s["pid"] == merged[-1]["pid"] and s["start"] == merged[-1]["end"]:
            merged[-1]["end"] = s["end"]
        else:
            merged.append(dict(s))
    return merged


ALGORITHMS = {
    "fcfs": fcfs,
    "sjf": sjf,
    "srtf": srtf,
    "priority_npp": priority_npp,
    "priority_pp": priority_pp,
    "round_robin": round_robin,
}


def run_scheduler(algorithm, processes, quantum=None):
    fn = ALGORITHMS[algorithm]
    return fn(processes, quantum=quantum)


def run_all(processes, quantum=2):
    return {name: fn(processes, quantum=quantum) for name, fn in ALGORITHMS.items()}
