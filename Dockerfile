FROM tiangolo/meinheld-gunicorn-flask:python3.7-alpine3.8

LABEL maintainer="Juan David Ayllón Burguillo <jdayllon@gmail.com>"

RUN apk --no-cache add build-base jpeg-dev jpeg zlib-dev

RUN pip install flask loguru pillow requests 

RUN apk del build-base libjpeg-turbo-dev jpeg-dev

# Add demo app
COPY ./app /app
