from rx.observable import Observable
from rx.anonymousobservable import AnonymousObservable
from rx.disposables import CompositeDisposable, \
    SingleAssignmentDisposable, SerialDisposable
from rx.concurrency import timeout_scheduler
from rx.internal import extensionmethod


@extensionmethod(Observable, alias="throttle_with_timeout")
def accumulated_debounce(self, duetime, scheduler=None):
    """Ignores values from an observable sequence which are followed by
    another value before duetime.
    Example:
    1 - res = source.debounce(5000) # 5 seconds
    2 - res = source.debounce(5000, scheduler)
    Keyword arguments:
    duetime -- {Number} Duration of the throttle period for each value
        (specified as an integer denoting milliseconds).
    scheduler -- {Scheduler} [Optional]  Scheduler to run the throttle
        timers on. If not specified, the timeout scheduler is used.
    Returns {Observable} The debounced sequence.
    """

    scheduler = scheduler or timeout_scheduler
    source = self

    def subscribe(observer):
        cancelable = SerialDisposable()
        value = []
        _id = [0]

        def on_next(x):
            value.append(x)
            _id[0] += 1
            current_id = _id[0]
            d = SingleAssignmentDisposable()
            cancelable.disposable = d

            def action(scheduler, state=None):
                if len(value) > 0 and _id[0] == current_id:
                    observer.on_next(value)
                del value[:]

            d.disposable = scheduler.schedule_relative(duetime, action)

        def on_error(exception):
            cancelable.dispose()
            observer.on_error(exception)
            del value[:]
            _id[0] += 1

        def on_completed():
            cancelable.dispose()
            if has_value[0]:
                observer.on_next(value[0])

            observer.on_completed()
            del value[:]
            _id[0] += 1

        subscription = source.subscribe(on_next, on_error, on_completed)
        return CompositeDisposable(subscription, cancelable)
    return AnonymousObservable(subscribe)
