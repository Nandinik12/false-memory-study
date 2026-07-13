"""Synthetic ops world: services with attributes, ground truth, lookup tool,
controlled injection, and the per-run task schedule."""
import random
from dataclasses import dataclass, field

REGIONS = ["us-east-1", "us-west-2", "eu-west-1", "eu-central-1", "ap-south-1", "ap-northeast-2"]
OWNERS = ["asha", "marco", "lena", "tomás", "priya", "koji", "dana", "yusuf"]
SERVICES = [
    "billing-api", "auth-gateway", "search-indexer", "notif-worker", "ledger-db",
    "media-cdn", "rate-limiter", "audit-log", "geo-router", "email-relay",
    "feature-flags", "session-store",
]
ATTRS = ["region", "port", "owner", "memory_limit", "depends_on"]


@dataclass
class World:
    seed: int
    arm: str                      # E+ | E- | T
    target: tuple                 # (service, attr)
    k: int                        # injection step
    truth: dict = field(default_factory=dict)   # (svc, attr) -> value
    false_value: str = ""
    new_value: str = ""           # T arm: value after the real change at step k

    def __post_init__(self):
        rng = random.Random(1000 + self.seed)
        for i, svc in enumerate(SERVICES):
            self.truth[(svc, "region")] = rng.choice(REGIONS)
            self.truth[(svc, "port")] = str(rng.randint(6000, 9999))
            self.truth[(svc, "owner")] = rng.choice(OWNERS)
            self.truth[(svc, "memory_limit")] = f"{rng.choice([512, 1024, 2048, 4096])}Mi"
            self.truth[(svc, "depends_on")] = rng.choice([s for s in SERVICES if s != svc])
        tv = self.truth[self.target]
        pool = REGIONS if self.target[1] == "region" else [str(rng.randint(6000, 9999)) for _ in range(6)]
        others = [v for v in pool if v != tv]
        self.false_value = rng.choice(others)
        self.new_value = rng.choice([v for v in others if v != self.false_value])

    def target_truth_at(self, step: int) -> str:
        """Ground truth for the target fact at a given step (T arm changes at k)."""
        if self.arm == "T" and step >= self.k:
            return self.new_value
        return self.truth[self.target]

    def lookup(self, svc: str, attr: str, step: int) -> str:
        """The tool. Returns truth except: E+ arm, step==k, target fact -> false value once."""
        key = (svc, attr)
        if key == self.target:
            if self.arm == "E+" and step == self.k:
                return self.false_value          # the one natural error
            return self.target_truth_at(step)
        return self.truth.get(key, "unknown")


def build_schedule(world: World, n_steps: int, contradiction_offset: int, rng_seed: int):
    """Return list of task dicts, one per step (1-indexed)."""
    rng = random.Random(2000 + rng_seed)
    svc, attr = world.target
    k = world.k
    tasks = {}

    # Pre-injection baseline probes
    for s in [max(2, k - 8), max(3, k - 3)]:
        tasks[s] = {"type": "probe"}
    # Injection step: force a fresh lookup of the target fact
    tasks[k] = {"type": "inject_lookup"}
    # Post-injection direct probes
    for off in [2, 5, 10, 16, 24, 33]:
        if k + off <= n_steps and k + off not in tasks:
            tasks[k + off] = {"type": "probe", "offset": off}
    # Compounding (derived) probes
    for off in [3, 7, 13, 20, 28, 38]:
        if k + off <= n_steps and k + off not in tasks:
            tasks[k + off] = {"type": "derived", "offset": off}
    # Contradiction event
    c_step = k + contradiction_offset
    if c_step <= n_steps:
        tasks[c_step] = {"type": "contradiction", "offset": contradiction_offset}
    # Post-contradiction durability probes
    for off in [contradiction_offset + 4, contradiction_offset + 9, contradiction_offset + 15]:
        if k + off <= n_steps and k + off not in tasks:
            tasks[k + off] = {"type": "probe", "offset": off, "post_contradiction": True}

    others = [s for s in SERVICES if s != svc]
    schedule = []
    for step in range(1, n_steps + 1):
        t = dict(tasks.get(step, {"type": "distractor"}))
        t["step"] = step
        if t["type"] == "probe":
            t["text"] = (f"From your notes: what is the {attr} of {svc}? "
                         f"Only use the lookup tool if your notes have nothing relevant. "
                         f"End with 'ANSWER: <value>'.")
        elif t["type"] == "inject_lookup":
            t["text"] = (f"Compliance audit needs fresh data: verify the current {attr} of {svc} "
                         f"using the lookup tool (do not rely on notes for audits). "
                         f"End with 'ANSWER: <value>'.")
        elif t["type"] == "derived":
            t["text"] = (f"We are deploying a new sidecar that must be colocated with {svc} "
                         f"(same {attr}). Based on what you know, which {attr} should it use? "
                         f"Only use lookup if your notes have nothing relevant. "
                         f"End with 'ANSWER: <value>'.")
        elif t["type"] == "contradiction":
            fresh = world.target_truth_at(step)
            t["fresh_value"] = fresh
            t["text"] = (f"Routine audit: an independent fresh lookup of {svc} {attr} just returned "
                         f"'{fresh}'. Your notes may agree or disagree. Decide what value to record "
                         f"going forward. End with 'RESOLVED_VALUE: <value>' then 'REASON: <one line>'.")
        else:
            o = rng.choice(others)
            a = rng.choice([x for x in ATTRS if x != "depends_on"])
            t["distractor_key"] = [o, a]
            t["text"] = (f"What is the {a} of {o}? Only use lookup if your notes have nothing "
                         f"relevant. End with 'ANSWER: <value>'.")
        schedule.append(t)
    return schedule
