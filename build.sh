#! /bin/bash

docker kill demo-flask-api
docker rm demo-flask-api  
docker rmi demo/api:0.0
docker build -t demo/api:0.0 .
docker run --name demo-flask-api -d -p 6969:5000 demo/api:0.0 -e PYTHONUNBUFFERED=1