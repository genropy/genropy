############################################################
# Dockerfile to build Genropy container images
# Based on Ubuntu
############################################################

FROM alpine:latest
RUN apk update
RUN apk add git
RUN apk add python3
RUN apk add py3-lxml
RUN apk add py3-psutil
RUN apk add py3-pip
RUN apk add --no-cache -X http://dl-cdn.alpinelinux.org/alpine/edge/testing py3-tzlocal
RUN apk add supervisor 
RUN apk add nginx 

RUN apk update \
  && apk add --virtual build-deps gcc python3-dev musl-dev \
  && apk add postgresql-dev \
  && pip install psycopg2 \
  && apk del build-deps

ADD . /home/genropy
RUN pip3 install paver

WORKDIR /home/genropy/gnrpy
RUN paver develop

RUN pip3 install psycopg2-binary


ENV GNRLOCAL_PROJECTS=/etc/workspaces

RUN python3 initgenropy.py
ADD supervisord.conf /etc/supervisor/conf.d/supervisord.conf



