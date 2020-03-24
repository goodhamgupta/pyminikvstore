import hashlib
import json
import logging
import os
import random
import socket
import sys
import time
from tempfile import NamedTemporaryFile

from typing import Any, Dict


def resp(start_response, code, headers=[("Content-type", "text/plain")], body=b""):
    start_response(code, headers)
    return [body]


if os.environ["TYPE"] == "master":
    # register volume servers
    volumes = os.environ["VOLUMES"].split(",")
    import plyvel

    db = plyvel.DB("/tmp/cachedb", create_if_missing=True)


def master(env: Dict[str, str], sr):
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
            return resp(sr, code="404 Not Found")
    else:
        # key found
        if request_type == "PUT":
            return resp(sr, code="409 Conflict")
        metakey = metakey.decode()
    volume = json.loads(metakey)["volume"]
    # send the redirect
    headers = [("location", f"http://{volume}/{key}")]
    return resp(sr, code="307 Temporary Redirect", headers=headers, body=metakey)


class FileCache(object):
    def __init__(self, basedir: str) -> None:
        self.basedir = os.path.realpath(basedir)
        self.tempdir = os.path.join(self.basedir, "tmp")
        os.makedirs(self.tempdir, exist_ok=True)

    def keytopath(self, key: str) -> str:
        # multilayer nginx
        assert len(key) == 32
        path = self.tempdir + "/" + key[0:1] + "/" + key[1:2]
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
        f = NamedTemporaryFile(dir=self.tempdir, delete=False)
        f.write(value)
        os.rename(f.name, self.keytopath(key))


if os.environ["TYPE"] == "volume":
    host = socket.gethostname()

    # create the filecache
    fc = FileCache(os.environ["VOLUME"])


def volume(env: Dict[str, Any], sr):
    key = env["REQUEST_URI"].encode("utf-8")[1:]
    hashed_key = hashlib.md5(key).hexdigest()
    request_type = env.get("REQUEST_METHOD")

    if request_type == "GET":
        if not fc.exists(hashed_key):
            # key not found in filecache
            return resp(
                sr,
                code="404 Not Found",
                headers=[("Content-Type", "text/plain")],
                body="Value not found for key: {}".format(key).encode(),
            )
        value = fc.get(hashed_key)
        return resp(
            sr,
            code="200 OK",
            headers=[("Content-Type", "text/plain")],
            body="Value: {}".format(value).encode(),
        )

    if request_type == "PUT":
        con_len = int(env.get("CONTENT_LENGTH", "0"))
        if con_len > 0:
            fc.put(hashed_key, env["wsgi.input"].read())
            return resp(
                sr,
                code="201 Created",
                headers=[("Content-Type", "text/plain")],
                body=f"Key {key} has been stored",
            )
        else:
            return resp(
                sr, code="411 Length Required", headers=[("Content-Type", "text/plain")]
            )

    if request_type == "DELETE":
        fc.delete(hashed_key)
        return resp(
            sr,
            code="202 Accepted",
            headers=[("Content-Type", "text/plain")],
            body=f"Key {key} has been deleted",
        )
