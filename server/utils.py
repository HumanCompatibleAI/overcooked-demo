from threading import Lock
from urllib.parse import urlparse

class ThreadSafeSet(set):

    def __init__(self, *args, **kwargs):
        super(ThreadSafeSet, self).__init__(*args, **kwargs)
        self.lock = Lock()
        

    def add(self, *args):
        with self.lock:
            retval = super(ThreadSafeSet, self).add(*args)
        return retval

    def clear(self, *args):
        with self.lock:
            retval = super(ThreadSafeSet, self).clear(*args)
        return retval

    def pop(self, *args):
        with self.lock:
            if len(self):
                retval = super(ThreadSafeSet, self).pop(*args)
            else:
                retval = None
        return retval

    def remove(self, item):
        with self.lock:
            if item in self:
                retval = super(ThreadSafeSet, self).remove(item)
            else:
                retval = None
        return retval

class ThreadSafeDict(dict):

    def __init__(self, *args, **kwargs):
        super(ThreadSafeDict, self).__init__(*args, **kwargs)
        self.lock = Lock()

    def clear(self, *args, **kwargs):
        with self.lock:
            retval = super(ThreadSafeDict, self).clear(*args, **kwargs)
        return retval

    def pop(self, *args, **kwargs):
        with self.lock:
            retval = super(ThreadSafeDict, self).pop(*args, **kwargs)
        return retval

    def __setitem__(self, *args, **kwargs):
        with self.lock:
            retval = super(ThreadSafeDict, self).__setitem__(*args, **kwargs)
        return retval

    def __delitem__(self, item):
        with self.lock:
            if item in self:
                retval = super(ThreadSafeDict, self).__delitem__(item)
            else:
                retval = None
        return retval

class GameError(Exception):
    pass

class SafeGameMethod(object):
    def __init__(self, f):
        self.func = f

    def __call__(self, *args, **kwargs):
        try:
            ret = self.func(*args, **kwargs)
            return ret
        except Exception as e:
            raise GameError(str(e))

    def __get__(self, instance, owner):
        from functools import partial
        return partial(self.__call__, instance)

def url_parser(url):
    o = urlparse(url)
    return o.scheme, o.netloc, o.path

def is_same_domain(url1, url2):
    _, domain1, _ = url_parser(url1)
    _, domain2, _ = url_parser(url2)
    return domain1 == domain2
