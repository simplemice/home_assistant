"""Track fresh device reports independently of commanded lock state."""


class ReportedLockStatus:
    """An ACK never changes status; commands and disconnects invalidate it."""

    def __init__(self, session, model, changed, *, retain_on_disconnect=False):
        self._session = session
        self._model = model
        self._changed = changed
        self._last_report = None
        self.locked = None
        self._closed = False
        self._retain_on_disconnect = retain_on_disconnect
        self.reported_at = None
        self.fresh = False
        self._listeners = set()
        self._unsubscribers = [
            session.register_callback(self._updated),
            session.register_disconnected_callback(self._disconnected),
        ]
        self._updated([])

    def subscribe(self, listener):
        """Subscribe to fresh physical reports, excluding invalidation and ACKs."""
        self._listeners.add(listener)
        return lambda: self._listeners.discard(listener)

    def invalidate(self):
        """Require a new report, even when unrelated datapoints are published."""
        if getattr(self._model, "sticky_lock_state", False):
            # Models whose lock state is pushed rarely keep the last known value.
            self.fresh = False
            self._changed()
            return
        report = self._model.lock_report
        self._last_report = report[0] if report is not None else None
        self.locked = None
        self.fresh = False
        self._changed()

    def _disconnected(self):
        self.fresh = False
        if not self._retain_on_disconnect:
            self.invalidate()
        else:
            self._changed()

    @property
    def available(self):
        return not self._closed

    def _updated(self, updates):
        if self._closed or not self._session.command_ready:
            return
        report = self._model.lock_report
        if report is not None and report[0] != self._last_report:
            self._last_report, self.locked = report
            self.reported_at = report[0]
            self.fresh = True
            for listener in tuple(self._listeners):
                listener(self.locked)
            self._changed()

    async def execute(self, action):
        """Called after command admission, immediately before the model action."""
        self.invalidate()
        await action()

    def close(self):
        self._closed = True
        self._listeners.clear()
        for unsubscribe in self._unsubscribers:
            unsubscribe()
        self._unsubscribers.clear()
        self.locked = None
