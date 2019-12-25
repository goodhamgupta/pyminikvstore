import os
import sys
import time


if os.environ["TYPE"] == "master":
    import plyvel

    db = plyvel.DB("/tmp/cachedb", create_if_missing=True)


def master(env, start_response):
    key = env.get("REQUEST_URI")[1:]
    request_type = env.get('REQUEST_METHOD')
    if request_type == "GET":
        print(key)
        metakey = db.get(key.encode('utf-8'))
        print("HERE")
        if metakey:
            # key found
            meta = json.loads(metakey)
            # send the redirect
            headers = [{'location': f"http://{meta.get('volume')}/{key}", 'expires': '100'}]
            start_response("302 Found", headers)
            return [meta]
        else:
            start_response("404 Not Found", [("Content-Type", "application/json")])
            return ["Value not found for key: {}".format(key).encode()]
    elif request_type == "PUT":
        # Fetch data from the payload and use db.put
        pass


if os.environ["TYPE"] == "volume":
    import socket

    host = socket.gethostname()


def volume(env, start_response):
    start_response("200 OK", [("Content-Type", "text/html")])
    return [b"Volume server mate"]
