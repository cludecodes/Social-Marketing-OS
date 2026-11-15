from app.automation import scheduler


def test_scheduler_start_is_idempotent_and_stop_shuts_it_down(monkeypatch):
    instances = []

    class FakeScheduler:
        def __init__(self, **kwargs):
            self.started = False
            self.stopped = False
            instances.append(self)

        def add_job(self, *args, **kwargs):
            pass

        def start(self):
            self.started = True

        def shutdown(self, wait):
            self.stopped = True

    monkeypatch.setattr(scheduler, "BackgroundScheduler", FakeScheduler)
    monkeypatch.setattr(scheduler, "get_schedule", lambda: {})
    monkeypatch.setattr(scheduler, "_scheduler", None)

    first = scheduler.start_scheduler()

    assert first.started
    assert scheduler.start_scheduler() is first
    assert len(instances) == 1

    scheduler.stop_scheduler()

    assert first.stopped
    assert scheduler._scheduler is None
