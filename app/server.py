import hashlib
import json
import logging
import os
import random
import socket
import sys
import time
import xattr
import requests
from tempfile import NamedTemporaryFile

from typing import Any, Dict


def resp(start_response, code, headers=[("Content-type", "text/plain")], body=b""):
    start_response(code, headers)
    return [body]


class SimpleKV:
    def __init__(self, fn):
        import plyvel

        self.db = plyvel.DB("/tmp/cachedb", create_if_missing=True)

    def put(self, k, v):
        self.db.put(k,v)

    def delete(self, k):
        self.delete(k)

    def


if os.environ["TYPE"] == "master":
    # register volume servers
    volumes = os.environ["VOLUMES"].split(",")
    db = SimpleKV(os.environ["DB"])


def master(env: Dict[str, str], sr):
    key = env.get("PATH_INFO")[1:]  # type: ignore
    request_type = env.get("REQUEST_METHOD")
    metakey = db.get(key.encode("utf-8"))

    if request_type == "POST":
        # POST is called by the volume servers to write to the database
        flen = int(env.get("CONTENT_LENGTH", "0"))
        if flen > 0:
            db.put(key.encode("utf-8"), env["wsgi.input"].read(), sync=True)
        else:
            db.delete(key.encode("utf-8"))
        return resp(sr, code="200 OK")

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
    """
    This is a single server key value store
    """

    def __init__(self, basedir: str) -> None:
        self.basedir = os.path.realpath(basedir)
        self.tempdir = os.path.join(self.basedir, "tmp")
        os.makedirs(self.tempdir, exist_ok=True)

    def keytopath(self, key: str) -> str:
        # multilayer nginx
        hashed_key = hashlib.md5(key).hexdigest()
        assert len(hashed_key) == 32
        path = self.tempdir + "/" + hashed_key[0:1] + "/" + hashed_key[1:2]
        if not os.path.isdir(path):
            os.makedirs(path, exist_ok=True)
        return os.path.join(path, hashed_key[2:])

    def exists(self, key: str) -> bool:
        return os.path.isfile(self.keytopath(key))

    def delete(self, key: str) -> None:
        try:
            os.unlink(self.keytopath(key))
            return True
        except FileNotFoundError:
            pass
        return False

    def get(self, key: str) -> bytes:
        return open(self.keytopath(key), "rb").read()

    def put(self, key: str, stream) -> None:
        f = NamedTemporaryFile(dir=self.tempdir, delete=False)
        # TODO: read in chunks to save ram
        # Save real name in xattr which will help rebuild db.
        xattr.set(f.name, "user.key", key)
        f.write(stream.read())
        # TODO: check hash
        os.rename(f.name, self.keytopath(key))


if os.environ["TYPE"] == "volume":

    # create the filecache
    fc = FileCache(os.environ["VOLUME"])


def volume(env: Dict[str, Any], sr):
    host = f"env['SERVER_NAME']:env['SERVER_PORT']"
    key = env["PATH_INFO"].encode("utf-8")[1:]
    request_type = env.get("REQUEST_METHOD")

    if request_type == "PUT":
        if fc.exists(key):
            # can't write, already exists
            return resp(sr, code="409 Conflict")
        con_len = int(env.get("CONTENT_LENGTH", "0"))
        if con_len > 0:
            # notify database
            response = requests.post(
                f"http://localhost:3000/{key.decode()}", json={"volume": host}
            )
            if response.status_code == 200:
                fc.put(key, env["wsgi.input"])
                return resp(
                    sr,
                    code="201 Created",
                    headers=[("Content-Type", "text/plain")],
                    body=f"Key {key} has been stored",
                )
            else:
                fc.delete(key)
                return resp(sr, code="500 Internal Server Error",)

        else:
            return resp(
                sr, code="411 Length Required", headers=[("Content-Type", "text/plain")]
            )

    if request_type == "GET":
        if not fc.exists(key):
            # key not found in filecache
            return resp(
                sr,
                code="404 Not Found",
                headers=[("Content-Type", "text/plain")],
                body="Value not found for key: {}".format(key).encode(),
            )
        value = fc.get(key)
        return resp(
            sr,
            code="200 OK",
            headers=[("Content-Type", "text/plain")],
            body="Value: {}".format(value).encode(),
        )

    if request_type == "DELETE":
        import pdb

        pdb.set_trace()
        response = requests.post(f"http://localhost:3000/{key.decode()}")
        if response.status_code == 200:
            if fc.delete(key):
                return resp(
                    sr,
                    code="202 Accepted",
                    headers=[("Content-Type", "text/plain")],
                    body=f"Key {key} has been deleted",
                )
            else:
                # file wasn't on disk
                return resp(sr, code="500 Internal Server Error")
        else:
            return resp(sr, code="500 Internal Server Error")
