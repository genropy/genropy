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
RUN apk add --no-cache -X http://dl-cdn.alpinelinux.org/alpine/edge/community py3-tzlocal
RUN apk add py3-psycopg2
RUN addgroup -S genro &&  adduser -S -D genro -G genro
COPY dojo_libs/dojo_11 /home/genro/genropy/dojo_libs/dojo_11
COPY gnrjs /home/genro/genropy/gnrjs
COPY gnrpy /home/genro/genropy/gnrpy
COPY gnrpy /home/genro/genropy/gnrpy
COPY projects/gnr_it /home/genro/genropy/projects/gnr_it
COPY projects/gnrcore /home/genro/genropy/projects/gnrcore
COPY resources /home/genro/genropy/resources
COPY scripts /home/genro/genropy/scripts
#COPY . /home/genro/genropy
COPY gnrfolder /home/genro/.gnr
RUN rm -fr /home/genro/genropy/.git
RUN pip3 install paver
WORKDIR /home/genro/genropy/gnrpy
RUN paver develop

RUN chown -R genro:genro /home/genro/genropy
RUN chown -R genro:genro /home/genro/.gnr


USER genro
WORKDIR /home/genro
ENV GNRLOCAL_PROJECTS=/etc/workspaces



