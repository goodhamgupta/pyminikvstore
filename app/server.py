import hashlib
import json
import logging
import os
import random
import socket
import sys
import time

from typing import Any, Dict


if os.environ["TYPE"] == "master":
    # register volume servers
    volumes = os.environ["VOLUMES"].split(",")
    import plyvel

    db = plyvel.DB("/tmp/cachedb", create_if_missing=True)


def master(env: Dict[str, str], start_response):
    key = env.get("REQUEST_URI")[1:]  # type: ignore
    request_type = env.get("REQUEST_METHOD")
    metakey = db.get(key.encode("utf-8"))

    if metakey is None:
        if request_type == "PUT":
            # TODO: Make volume selection better
            volume = random.choice(volumes)

            # save volume to database
            metakey = json.dumps({"volume": volume})
            db.put(key.encode(), metakey.encode())
        else:
            # this key doesn't exist and we aren't trying to create it
            start_response("404 Not Found", [("Content-Type", "application/json")])
            return ["Value not found for key: {}".format(key).encode()]
    else:
        # key found
        """
        if request_type == "PUT":
            start_response("409 Conflict", [("Content-Type", "application/json")])
            return ["Key already exists!"]
        """
        meta = json.loads(metakey)
    # send the redirect
    volume = meta["volume"]
    # send the redirect
    headers = [("location", f"http://{volume}/{key}")]
    start_response("307 Temporary Redirect", headers)
    return [meta]


class FileCache(object):
    def __init__(self, basedir: str) -> None:
        self.basedir = os.path.realpath(basedir)
        os.makedirs(basedir, exist_ok=True)

    def keytopath(self, key: str) -> str:
        # multilayer nginx
        assert len(key) == 32
        path = self.basedir + "/" + key[0:1] + "/" + key[1:2]
        if not os.path.isdir(path):
            os.makedirs(path, exist_ok=True)
        return os.path.join(path, key[2:])

    def exists(self, key: str) -> bool:
        return os.path.isfile(self.keytopath(key))

    def delete(self, key: str) -> None:
        os.unlink(self.keytopath(key))

    def get(self, key: str) -> bytes:
        return open(self.keytopath(key), "rb").read()

    def put(self, key: str, value: bytes) -> None:
        with open(self.keytopath(key), "wb") as file:
            file.write(value)


if os.environ["TYPE"] == "volume":
    host = socket.gethostname()

    # create the filecache
    fc = FileCache(os.environ["VOLUME"])


def volume(env: Dict[str, Any], start_response):
    key = env["REQUEST_URI"].encode("utf-8")[1:]
    hashed_key = hashlib.md5(key).hexdigest()
    request_type = env.get("REQUEST_METHOD")

    if request_type == "GET":
        if not fc.exists(hashed_key):
            # key not found in filecache
            start_response("404 Not Found", [("Content-Type", "application/json")])
            return ["Value not found for key: {}".format(key).encode()]
        value = fc.get(hashed_key)
        start_response("200 OK", [("Content-Type", "application/json")])
        return ["Value: {}".format(value).encode()]

    if request_type == "PUT":
        fc.put(hashed_key, env["wsgi.input"].read())
        start_response("201 Created", [("Content-Type", "application/json")])
        return [f"Key {key} has been stored"]
    if request_type == "DELETE":
        fc.delete(hashed_key)
        start_response("202 Accepted", [("Content-Type", "application/json")])
        return [f"Key {key} has been deleted"]
