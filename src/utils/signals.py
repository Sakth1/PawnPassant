class SignalBus:
    def __init__(self):
        self._listeners = {}

    def connect(self, event_type, fn):
        self._listeners.setdefault(event_type, []).append(fn)

    def emit(self, event):
        event_type = type(event)

        for fn in self._listeners.get(event_type, []):
            fn(event)


bus = SignalBus()
