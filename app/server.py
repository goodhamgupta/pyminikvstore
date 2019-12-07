import os
import sys
import time


if os.environ["TYPE"] == "master":
    import plyvel
    db = plyvel.DB("/tmp/cachedb", create_if_missing=True)


def master(env, start_response):
    print(env)
    key = env.get("REQUEST_URI")
    value = db.get(key.encode())
    print(value)
    if value:
        start_response("200 OK", [("Content-Type", "application/json")])
        return [b" {}: {}".format(key, value)]
    db.put(b"key", b"wtf_mate")
    start_response("500 ERROR", [("Content-Type", "application/json")])
    return [b"Not found"]
    #print("error")
    #for i in db.iterator():
    #    print("in loop")
    #    print(i)


def volume(env, start_response):
    start_response("200 OK", [("Content-Type", "text/html")])
    return [b"Volume server mate"]
