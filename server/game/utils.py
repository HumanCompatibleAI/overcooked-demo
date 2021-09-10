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