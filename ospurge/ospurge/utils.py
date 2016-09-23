import logging
import time


def call_until_true(func: callable, timeout: int=10, sleep_for: float=1.0):
    """Call the given function until it returns True (and return True)
    or until the specified duration (in seconds) elapses (and return False).

    :param func: A zero argument callable that returns True on success.
    :param timeout: The number of seconds for which to attempt a
        successful call of the function.
    :param sleep_for: The number of seconds to sleep after an unsuccessful
        invocation of the function.
    """
    now = time.time()
    _timeout = now + timeout
    while now < _timeout:
        if func():
            return True
        logging.debug("Function '%s' is going to sleep for %.2f",
                      func.__name__, sleep_for)
        time.sleep(sleep_for)
        now = time.time()

    raise RuntimeError("Timeout exceeded waiting for {} to complete".format(
        func.__name__))
