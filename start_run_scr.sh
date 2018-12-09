
if [ $# -ne 1 ]; then
  echo "1 arguments are required." 1>&2
  exit 1
fi
sudo python ./src/main.py run_scr ./conf/production.ini tatsuki923/door_app my_service 0 $1
