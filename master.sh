export VOLUMES=${1:-localhost:3001}
export TYPE='master'
uwsgi --ini uwsgi_master.ini
