#!/bin/bash

# 1st argument env migration metor
# 2st argument env image_name 
# 3st argument env container_name
# 4st argument env network bandwidth

if [ $# -ne 4 ]; then
  echo "given arguments are $#." 1>&2
  echo "4 arguments are required." 1>&2
  exit 1
fi

COUNTER=5
TMP_NUM=0
BANDWIDTH_UNIT="Mbit"

start_container() {
  #1st image_name
  #2nd container_name
  #3nd metor
  echo "start container $2"
  if [ $1 = "tatsuki/migration_ev" ]; then
    #docker run -d --name $2 --ipc=host -v /tmp/:/tmp/ $1 sh -c './service_api/client'
    docker run -d --name $2 --ipc=host -v /tmp/:/tmp/ $1 sh -c 'i=0; while true; do echo $i; i=$(expr $i + 1); sleep 1; done'
  elif [ $1 = "busybox" ]; then
    docker run --name $2 -d $1 sh -c 'i=0; while true; do echo $i; i=$(expr $i + 1); sleep 1; done'
  elif [ $1 = "elasticsearch" ]; then
    docker run --name $2 -p 9200:9200 -d $1
  else
    echo "Input valid image name"
    exit 1
  fi

  if [ $3 = "con" ]; then
    sshpass -p dkw9srmd ssh miura@192.168.1.2 docker run --name repo -d -p 5000:5000 registry:2
  fi
}

delete_src_container() {
  #1st container_name
  docker rm -f $1
}

delete_dst_container() {
  #1st container_name
  sshpass -p dkw9srmd ssh miura@192.168.1.2 docker rm -f $1
}

delete_containers() {
  #1st container_name
  #2nd metor
  delete_src_container $1
  delete_dst_container $1

  if [ $2 = "con" ]; then
    docker rmi -f $(docker images --filter=reference="192.168.1.2:5000/*" -q)
    sudo systemctl restart docker
    sshpass -p dkw9srmd ssh miura@192.168.1.2 docker rmi -f $(sshpass -p dkw9srmd ssh miura@192.168.1.2 docker images --filter=reference="localhost:5000/*" -q)

    echo 'stop repo on dst'
    sshpass -p dkw9srmd ssh miura@192.168.1.2 docker stop repo
    sshpass -p dkw9srmd ssh miura@192.168.1.2 docker rm repo
  fi
}

run() {
  #1st metor
  #2nd image_name 
  #3rd container_name
  #4th bandwidth
  echo "run worker"
  if [ $1 = "prop" ]; then
    sudo python ./src/main.py run_prop ./conf/production.ini $2 $3 $4
  elif [ $1 = "con" ]; then
    sudo python ./src/main.py run_con ./conf/production.ini $2 $3 $4
  else
    echo "Please input valid migration metor"
    exit 1
  fi
}

change_network_bandwidth() {
  echo "set network bandwidth"
  sudo tc qdisc add dev eno1 root tbf limit $1 buffer 200Kb rate $1
}

release_network_setting (){
  echo "release network bandwidth settings"
  sudo tc qdisc del dev eno1 root
}

release_network_setting
if [ $4 -ne 0 ]; then
  change_network_bandwidth $4$BANDWIDTH_UNIT
fi

while [ "$TMP_NUM" -lt "$COUNTER" ]
do
  start_container $2 $3$TMP_NUM $1
  echo "sleep 10 seconds...."
  sleep 10
  run $1 $2 $3$TMP_NUM $4
  echo "sleep....."
  sleep 1
  delete_containers $3$TMP_NUM $1
  echo "fin container $3$TMP_NUM"
  echo "sleep 10 seconds...."
  sleep 10 # avoid docker error (restart too quickly)
  let TMP_NUM++
done

release_network_setting
echo "Fin"

