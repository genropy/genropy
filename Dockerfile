############################################################
# Dockerfile to build Genropy container images
# Based on Alpine
############################################################

FROM python:3.14.0a1-slim
RUN apt-get update && apt-get -y full-upgrade &&  apt-get autoremove -y
RUN pip install --upgrade pip
RUN adduser --group --system --home /home/genro genro
COPY dojo_libs/dojo_11 /home/genro/genropy/dojo_libs/dojo_11
COPY gnrjs /home/genro/genropy/gnrjs
COPY gnrpy /home/genro/genropy/gnrpy
COPY projects/gnr_it /home/genro/genropy/projects/gnr_it
COPY projects/gnrcore /home/genro/genropy/projects/gnrcore
COPY resources /home/genro/genropy/resources
COPY webtools /home/genro/genropy/webtools
COPY gnrfolder /home/genro/.gnr
RUN rm -fr /home/genro/genropy/.git

WORKDIR /home/genro/genropy/gnrpy
RUN pip install .[developer,pgsql]

RUN chown -R genro:genro /home/genro/genropy
RUN chown -R genro:genro /home/genro/.gnr
WORKDIR /home/genro
ENV GNRLOCAL_PROJECTS=/etc/workspaces



