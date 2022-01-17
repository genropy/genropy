############################################################
# Dockerfile to build Genropy container images
# Based on Alpine
############################################################

FROM alpine:3.14
RUN apk update
RUN apk add git
RUN apk add python3
RUN apk add py3-lxml
RUN apk add py3-psutil
RUN apk add py3-pip
RUN apk add --no-cache -X http://dl-cdn.alpinelinux.org/alpine/edge/testing py3-tzlocal
  
COPY . /root/genropy
COPY gnrfolder /root/.gnr
RUN pip3 install paver
WORKDIR /root/genropy/gnrpy
RUN paver develop

ENV GNRLOCAL_PROJECTS=/etc/workspaces



