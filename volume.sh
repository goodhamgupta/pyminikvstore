export TYPE="volume"
export MASTER="127.0.0.1:3131"
export VOLUME="/tmp/volume1"
uwsgi --ini uwsgi_volume.ini
