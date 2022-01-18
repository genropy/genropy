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
RUN addgroup -S genro &&  adduser -S -D genro -G genro
COPY . /home/genro/genropy
COPY gnrfolder /home/genro/.gnr
RUN rm -fr /home/genro/genropy/.git
RUN pip3 install paver
WORKDIR /home/genro/genropy/gnrpy
RUN paver develop
RUN chown -R genro:genro /home/genro/genropy
USER genro
WORKDIR /home/genro
ENV GNRLOCAL_PROJECTS=/etc/workspaces



