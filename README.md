# pyminikvstore

Implementation of a robust and production-level KV store. This is a built using the screencast by George Hotz availabe [here](https://www.youtube.com/watch?v=cAFjZ1gXBxc) with a few changes to the design.

This implementation will store KV pairs. It is like nginx has but with filenames as MD5 hash and the real key present in the xattr of the file.

## Implementation

- It will ahve two endpoints:
- `PUT`: 
  - Put a value in the store. 
  - Blocking operation. 
  - If 200 => Key written.
  - Anything else => Key was not written
- `GET`:
  - Fetch the value for a key
- `DELETE`
  -  Delete a key from the DB.  - We will be using LevelDB for the KV store.
- **Caevats**
  - Only one process can open the DB at a time
## Types of servers

- Master
  - Keeps track of the metadata i.e the keys
- Volume
  - Responsible for actually storing the data

## Running the server

```
./server.sh /tmp/cachedb
./volume.sh /tmp/volume1
./volume.sh /tmp/volume2
```

## Notes

- `reload-mercy` and `worker-reload-mercy` help kill the uwsgi workers faster. Refer the github thread present [here](https://github.com/unbit/uwsgi/issues/844#issuecomment-455756013)

## Usage

```
curl -L -X PUT -d ever http://localhost:3000/greatest
curl -L -X GET http://localhost:3000/greatest
curl -L -X DELETE http://localhost:3000/greatest
```
