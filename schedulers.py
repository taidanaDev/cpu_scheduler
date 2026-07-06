#CPU Scheduling Algorithms

def _pid_key(p):
    # Sorts by PID number, fallback to string
    pid = p["pid"]
    digits = "".join(ch for ch in pid if ch.isdigit())
    return (int(digits) if digits else 0, pid)

def _priority_sort_key(p, priority_convention="lower"):
    """
    Priority convention:
    - "lower"  means lower number = higher priority
    - "higher" means higher number = higher priority
    """
    if priority_convention == "higher":
        return (-p["priority"], p["arrival"], _pid_key(p))

    return (p["priority"], p["arrival"], _pid_key(p))

def _init_metrics(processes):
    metrics = {}
    for p in processes:
        metrics[p["pid"]] = {
            "arrival": p["arrival"],
            "burst": p["burst"],
            "start": None,
            "waiting": 0,
            "turnaround": 0,
            "end": 0,
        }
    return metrics


def _finalize(processes, timeline, log, metrics):
    n = len(processes)
    avg_wait = sum(m["waiting"] for m in metrics.values()) / n if n else 0
    avg_turn = sum(m["turnaround"] for m in metrics.values()) / n if n else 0

    return {
        "timeline": timeline,
        "log": log,
        "metrics": metrics,
        "averages": {
            "waiting": round(avg_wait, 2),
            "turnaround": round(avg_turn, 2),
        },
    }


def _add_idle_if_needed(timeline, log, current_time, next_time):
    if next_time > current_time:
        timeline.append({"pid": "IDLE", "start": current_time, "end": next_time})
        log.append({"time": current_time, "message": f"CPU idle, no process ready until t={next_time}"})
    return next_time



# Non-preemptive Algorithms: FCFS, SJF, Priority (NPP)

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

        metrics[chosen["pid"]]["start"] = start
        metrics[chosen["pid"]]["end"] = end
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
        return f"{chosen['pid']} arrived earliest among ready processes → run (burst={chosen['burst']})"

    return _run_non_preemptive(processes, select, describe)


def sjf(processes, **kwargs):
    def select(ready):
        return min(ready, key=lambda p: (p["burst"], p["arrival"], _pid_key(p)))

    def describe(chosen, ready, t):
        others = ", ".join(f"{p['pid']}={p['burst']}" for p in ready if p["pid"] != chosen["pid"])
        extra = f" (others ready: {others})" if others else ""
        return f"{chosen['pid']} has shortest burst ({chosen['burst']}) among ready processes → run{extra}"

    return _run_non_preemptive(processes, select, describe)


def priority_npp(processes, priority_convention="lower", **kwargs):
    def select(ready):
        return min(ready, key=lambda p: _priority_sort_key(p, priority_convention))

    def describe(chosen, ready, t):
        if priority_convention == "higher":
            rule = "higher number = higher priority"
        else:
            rule = "lower number = higher priority"

        return (
            f"{chosen['pid']} has highest priority "
            f"(value={chosen['priority']}, rule: {rule}) among ready → run"
        )

    return _run_non_preemptive(processes, select, describe)


# Preemptive Algorithms: SRTF, Priority (PP), Round Robin

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

        if metrics[chosen["pid"]]["start"] is None:
            metrics[chosen["pid"]]["start"] = time

        if chosen["pid"] != running_pid:
            if running_pid is not None:
                timeline.append({"pid": running_pid, "start": slice_start, "end": time})
                prev_remaining = procs[running_pid]["remaining"]
                log.append({
                    "time": time,
                    "message": f"{chosen['pid']} (remaining={chosen['remaining']}) < {running_pid} "
                               f"(remaining={prev_remaining}) → PREEMPT {running_pid}, run {chosen['pid']}",
                })
            else:
                log.append({"time": time, "message": f"{chosen['pid']} has shortest remaining time ({chosen['remaining']}) → run"})
            running_pid = chosen["pid"]
            slice_start = time

        chosen["remaining"] -= 1
        time += 1

        if chosen["remaining"] == 0:
            timeline.append({"pid": chosen["pid"], "start": slice_start, "end": time})
            running_pid = None
            metrics[chosen["pid"]]["end"] = time
            metrics[chosen["pid"]]["turnaround"] = time - chosen["arrival"]
            metrics[chosen["pid"]]["waiting"] = metrics[chosen["pid"]]["turnaround"] - chosen["burst"]
            log.append({"time": time, "message": f"{chosen['pid']} completes"})
            completed += 1

    timeline = _merge_adjacent(timeline)
    return _finalize(processes, timeline, log, metrics)


def priority_pp(processes, priority_convention="lower", **kwargs):
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

        chosen = min(ready, key=lambda p: _priority_sort_key(p, priority_convention))

        if metrics[chosen["pid"]]["start"] is None:
            metrics[chosen["pid"]]["start"] = time

        if chosen["pid"] != running_pid:
            rule = "higher number = higher priority" if priority_convention == "higher" else "lower number = higher priority"

        if running_pid is not None:
            timeline.append({"pid": running_pid, "start": slice_start, "end": time})
            prev_priority = procs[running_pid]["priority"]

            log.append({
                "time": time,
                "message": (
                    f"{chosen['pid']} priority={chosen['priority']} is higher than "
                    f"{running_pid} priority={prev_priority} "
                    f"({rule}) → PREEMPT {running_pid}, run {chosen['pid']}"
                )
            })

        else:
            log.append({
                "time": time,
                "message": (
                    f"{chosen['pid']} has highest priority "
                    f"({chosen['priority']}, rule: {rule}) → run"
                )
            })

        running_pid = chosen["pid"]
        slice_start = time

        chosen["remaining"] -= 1
        time += 1

        if chosen["remaining"] == 0:
            timeline.append({"pid": chosen["pid"], "start": slice_start, "end": time})
            running_pid = None
            metrics[chosen["pid"]]["end"] = time
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
        next_arrival = arrivals_sorted[arrival_idx]["arrival"]
        time = _add_idle_if_needed(timeline, log, time, next_arrival)

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

        if metrics[pid]["start"] is None:
            metrics[pid]["start"] = start

        timeline.append({"pid": pid, "start": start, "end": end})
        log.append({
            "time": start,
            "message": f"{pid} runs for {run_for} unit(s) (quantum={quantum}, remaining before={p['remaining']})",
        })

        p["remaining"] -= run_for
        time = end

        # Arrivals take priority over re-queued process.
        while arrival_idx < n and arrivals_sorted[arrival_idx]["arrival"] <= time:
            newly = arrivals_sorted[arrival_idx]["pid"]
            queue.append(newly)
            log.append({"time": time, "message": f"{newly} arrives → enqueued"})
            arrival_idx += 1

        if p["remaining"] > 0:
            queue.append(pid)
            log.append({"time": time, "message": f"{pid} quantum expired, {p['remaining']} remaining → re-enqueued"})
        else:
            metrics[pid]["end"] = time
            metrics[pid]["turnaround"] = time - p["arrival"]
            metrics[pid]["waiting"] = metrics[pid]["turnaround"] - p["burst"]
            log.append({"time": time, "message": f"{pid} completes"})
            completed += 1

    return _finalize(processes, timeline, log, metrics)


def _merge_adjacent(timeline):
    # Merge back-to-back slices of the same pid (clean-up for Gantt chart).
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


def run_scheduler(algorithm, processes, quantum=None, priority_convention="lower"):
    fn = ALGORITHMS[algorithm]
    return fn(
        processes,
        quantum=quantum,
        priority_convention=priority_convention
    )

def run_all(processes, quantum=2, priority_convention="lower"):
    return {
        name: fn(
            processes,
            quantum=quantum,
            priority_convention=priority_convention
        )
        for name, fn in ALGORITHMS.items()
    }