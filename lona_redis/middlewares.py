import pickle
import sys

import redis
# FIXME remove this
from loguru import logger


class RedisSession:
    # FIXME this isn't used - can be removed?
    # def __init__(self, redis_user):
    #   self.redis_user = redis_user

    def __init__(self, *args, **kwargs):
        """
        initalize redis.Redis()

        https://redis.readthedocs.io/en/latest/#quickly-connecting-to-redis

        but there are many many kwargs:
        https://redis.readthedocs.io/en/latest/connections.html
        """

        # FIXME suggest to pass kwargs through to redis.Redis
        self.r = redis.Redis(**kwargs)

    def redis_key(self, user_key):
        """
        combine self.user_request_session_key with user's key
        so that the ACTUAL key used to store value in Redis is unique
        """

        COMBINE_CHR = ":"
        return self.user_request_session_key + COMBINE_CHR + user_key

    def set(self, *args, **kwargs):
        """
        user should call this to easily set values
        eg. request.user.session.set("foo",123)
        or
        eg. request.user.session.set(foo=123, bar="hello")

        pickle all values so that Redis can store any pickle-able Python value
        """

        if len(args) > 0:
            # eg. request.user.session.set("foo",123)
            if len(args) != 2:
                class_name = self.__class__.__name__
                function_name = sys._getframe().f_code.co_name
                raise TypeError(
                    f"{__name__}.{class_name}.{function_name} expected 2 arguments, got {len(args)}"
                )
            else:
                actual_redis_key = self.redis_key(args[0])
                self.r.set(actual_redis_key, pickle.dumps(args[1]))

        for user_key, value in kwargs.items():
            # eg. request.user.session.set(foo=123, bar="hello")
            actual_redis_key = self.redis_key(user_key)
            self.r.set(actual_redis_key, pickle.dumps(value))

    # def get(self, *args, **kwargs):
    #    raise NotImplementedError()

    def get(self, *args):
        """
        user should call this to easily get values
        eg. request.user.session.get("foo")
        or
        eg. request.user.session.get("foo", "bar", "baz")
            return tuple of values

        un-pickle all values that were retrieved from Redis
        """
        if len(args) == 1:
            # eg. request.user.session.get("foo")
            user_key = args[0]
            actual_redis_key = self.redis_key(user_key)
            return pickle.loads(self.r.get(actual_redis_key))

        else:
            # eg. request.user.session.get("foo", "bar", "baz")
            values = ()
            for user_key in args:
                actual_redis_key = self.redis_key(user_key)
                value = pickle.loads(self.r.get(actual_redis_key))
                values = values + (value,)

            return values


# FIXME this isn't used - can be removed?
# class RedisUser:
#    def __init__(self, connection):
#        # self.connection = connection
#        # self.session = RedisSession(self)
#        pass
#
#    def __eq__(self, other):
#        raise NotImplementedError()


class RedisSessionMiddleware:
    async def on_startup(self, data):
        """
        initalize Redis connection
        """

        settings = data.server.settings

        # FIXME how to set Redis connection settings?
        # there are many many kwargs (https://redis.readthedocs.io/en/latest/connections.html)
        # FIXME maybe settings should be a dict instead

        # FIXME remove this
        # logger.debug(f"{settings.REDIS_USER=}")
        # logger.debug(f"{settings.REDIS_PASSWORD=}")

        # common setting, using default args (ie. host="localhost", port=6379, db=0)
        # self.redis_session = RedisSession()

        # FIXME suggested way to pass & use Redis connection settings
        # logger.debug(f"{settings.REDIS_CONNECTION=}")
        self.redis_session = RedisSession(**settings.REDIS_CONNECTION)

        # initalize this here, but to be set in handle_request()
        # just prior to user calling request.user.session.get(), request.user.session.set()
        self.user_request_session_key = None

        return data

    # FIXME this isn't used - can be removed?
    # def handle_connection(self, data):
    #    # connection.user = RedisUser(data.connection)
    #
    #    return data

    def handle_request(self, data):
        request = data.request

        # set self.user_request_session_key to request.user.session_key
        # so that subsequent calls by the user to
        # self.redis_session.set, self.redis_session.get
        #   ie. in app->View->handle_request() : request.user.session.set(), request.user.session.get()
        # will have request.user.session_key available
        # we NEED this so that each Redis key is unique to request.user.session_key
        self.redis_session.user_request_session_key = request.user.session_key
        request.user.session = self.redis_session

        return data
