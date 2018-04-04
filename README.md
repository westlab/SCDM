# Smart-Community-Docker-Manager
## Dependencies
- Python 3.5.1
- Docker 17.09.1-ce
- criu v3.7

## Install Python modules
```console
$ pip install -r requirements.txt
```

## Setup
```console
# Run Rest Server
$ python ./src/main.py rest ./conf/[development.ini/production.ini]


# Run RPC Server
$ python ./src/main.py rpc ./conf/[development.ini/production.ini]
```

## File Organization

```
smart-community-docker-manager
├── conf ------------------------------- configuration files
├── logs ------------------------------- log files
├── requirements.txt ------------------- requirements text
└── src -------------------------------- src codes
    ├── main.py ------------------------ main execution file
    ├── service ------------------------ A group of services that peform specific processing
    │   ├── api.py
    │   ├── codegen.py
    │   └── grpc_server.py
    ├── settings ----------------------- Setting files
    └── tool --------------------------- General-purpose tools that are specified in service
        ├── docker_api.py
        ├── docker_base_api.py
        ├── migration_worker.py
        ├── common
        └── gRPC
 ```
