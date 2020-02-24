import hashlib
import os
import socket
import sys
import time


if os.environ["TYPE"] == "master":
    import plyvel

    db = plyvel.DB("/tmp/cachedb", create_if_missing=True)


def master(env, start_response):
    key = env.get("REQUEST_URI")[1:]
    request_type = env.get("REQUEST_METHOD")
    metakey = db.get(key.encode("utf-8"))

    if metakey is None:
        if request_type == "PUT":
            # TODO handle putting key
            pass
        # this key doesn't exist and we aren't trying to create it
        start_response("404 Not Found", [("Content-Type", "application/json")])
        return ["Value not found for key: {}".format(key).encode()]

    # key found
    meta = json.loads(metakey)
    # send the redirect
    headers = [{"location": f"http://{meta.get('volume')}/{key}", "expires": "100"}]
    start_response("302 Found", headers)
    return [meta]


class FileCache(object):
    def __init__(self, basedir):
        self.basedir = os.path.realpath(basedir)
        os.makedirs(basedir)

    def keytopath(self, key):
        # multilayer nginx
        assert len(key) == 16
        path = basedir + "/" + key[0:1] + "/" + key[1:2]
        if not os.path.isdir(path):
            os.makedirs(path)
        return os.path.join(path, key[2:])

    def exists(self, key):
        return os.path.isfile(self.keytopath(key))

    def delete(self, key):
        os.path.unlink(self.keytopath(key))

    def get(self, key):
        return open(self.keytopath(key), "rb").read()

    def put(self, key, value):
        with open(self.keytopath(key), "wb") as file:
            file.write(value)
        pass


if os.environ["TYPE"] == "volume":
    host = socket.gethostname()

    # register with master
    master = os.environ["MASTER"]

    # create the filecache
    FileCache(os.environ["VOLUME"])


def volume(env, start_response):
    key = env["REQUEST_URI"].encode("utf-8")
    hashed_key = hashlib.md5(key).hexdigest()
    request_type = env.get("REQUEST_METHOD")

    if request_type == "GET":
        if not fc.exists(key):
            # key not found in filecache
            start_response("404 Not Found", [("Content-Type", "application/json")])
            return ["Value not found for key: {}".format(key).encode()]
    return FileCache.get(hkey)

    if request_type == "PUT":
        fc.put(hashed_key, env["wsgi.input"].read(env["CONTENT_LENGTH"]))
    if request_type == "DELETE":
        fc.delete(hashed_key)
