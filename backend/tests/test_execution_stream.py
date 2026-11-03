import json
import unittest
from datetime import UTC, datetime
from uuid import uuid4

from app.api.tasks import stream_frames
from app.schemas.process import EventOut, ExecutionOut

RUN = uuid4()


def execution(status):
    return ExecutionOut(task_id=uuid4(), execution_id=RUN, requirement="Show revenue by product",
                        status=status, current_stage="execution", created_at=datetime.now(UTC), plan=None, result=None)


def event(sequence):
    return EventOut(execution_id=RUN, sequence=sequence, stage="execution", event_type="step_started",
                    message=f"event {sequence}", payload_json={}, created_at=datetime.now(UTC))


def frames(states, after=0, max_seconds=60):
    calls = []

    def load(cursor):
        calls.append(cursor)
        return states[min(len(calls) - 1, len(states) - 1)]

    tick = iter(range(10_000))
    out = list(stream_frames(load, after, sleep=lambda _: None, max_seconds=max_seconds, clock=lambda: next(tick)))
    return out, calls


class ExecutionStreamTests(unittest.TestCase):
    def test_sends_new_events_once_and_ends_when_finished(self):
        running = execution("running")
        out, calls = frames([(running, [event(1), event(2)]), (running, [event(3)]), (execution("succeeded"), [])])
        kinds = [frame.split("\n")[1] if frame.startswith("id:") else frame.split("\n")[0] for frame in out]
        self.assertEqual(kinds.count("event: event"), 3)
        self.assertEqual(kinds.count("event: execution"), 2)   # unchanged run state is not resent
        self.assertEqual(out[-1], "event: done\ndata: {}\n\n")
        self.assertEqual(calls, [0, 2, 3])                       # the cursor advances past sent events

    def test_resumes_after_the_given_sequence(self):
        _, calls = frames([(execution("failed"), [])], after=7)
        self.assertEqual(calls, [7])

    def test_waiting_runs_stay_open_until_the_time_limit(self):
        out, _ = frames([(execution("waiting_input"), [])], max_seconds=3)
        self.assertNotIn("event: done\ndata: {}\n\n", out)
        frame = next(f for f in out if f.startswith("event: execution"))
        self.assertEqual(json.loads(frame.split("data: ", 1)[1])["status"], "waiting_input")


if __name__ == "__main__":
    unittest.main()
