#!/bin/bash
# run with gunicorn (http://docs.gunicorn.org/en/stable/run.html#gunicorn)
echo "Starting the container..."
exec gunicorn --chdir app  -b :5000 hello:app