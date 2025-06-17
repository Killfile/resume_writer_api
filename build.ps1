docker kill demo-flask-api
docker rm demo-flask-api  
docker rmi demo/api:0.0
docker build -t demo/api:0.0 . --no-cache
docker run --name demo-flask-api -d -p 5000:5000 `
  -v ${PWD}\mounted_files:/home/flask-api/mounted_files `
  -v ${PWD}\app:/home/flask-api/app `
  demo/api:0.0