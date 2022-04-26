############################################################
# Dockerfile to build Genropy container images
# Based on Alpine
############################################################

FROM alpine:latest
RUN apk update
RUN apk add git
RUN apk add python3
RUN apk add py3-lxml
RUN apk add py3-psutil
RUN apk add py3-pip
RUN apk add --no-cache -X http://dl-cdn.alpinelinux.org/alpine/edge/testing py3-tzlocal
  
ADD . /home/genropy
RUN pip3 install paver

WORKDIR /home/genropy/gnrpy
RUN paver develop

ENV GNRLOCAL_PROJECTS=/etc/workspaces

RUN python3 initgenropy.py --no_user



