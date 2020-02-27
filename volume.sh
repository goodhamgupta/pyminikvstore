export TYPE="volume"
export VOLUME="/tmp/volume1"
# If you want to use debugger, use --honour-stdin
uwsgi --ini uwsgi_volume.ini --honour-stdin
