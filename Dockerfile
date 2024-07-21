############################################################
# Dockerfile to build Genropy container images
# Based on Alpine
############################################################

FROM python:3.13.0b3-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
        libxml2-dev \
        libxslt1-dev \
        libxslt-dev \
        libyajl2 \
        libglib2.0-0 \
        libpango-1.0-0 \
        libpangoft2-1.0-0 -y && \
    rm -r /var/lib/apt/lists/* && \
    apt-get autoremove -y
RUN pip install -U psycopg2-binary tzlocal paver pillow weasyprint pyPdf2
RUN adduser --system --group genro
COPY dojo_libs/dojo_11 /home/genro/genropy/dojo_libs/dojo_11
COPY gnrjs /home/genro/genropy/gnrjs
COPY gnrpy /home/genro/genropy/gnrpy
COPY projects/gnr_it /home/genro/genropy/projects/gnr_it
COPY projects/gnrcore /home/genro/genropy/projects/gnrcore
COPY resources /home/genro/genropy/resources
COPY scripts /home/genro/genropy/scripts
#COPY . /home/genro/genropy
COPY gnrfolder /home/genro/.gnr
RUN rm -fr /home/genro/genropy/.git
RUN pip install paver
WORKDIR /home/genro/genropy/gnrpy
RUN paver develop

RUN chown -R genro:genro /home/genro/genropy
RUN chown -R genro:genro /home/genro/.gnr


#USER genro
WORKDIR /home/genro
ENV GNRLOCAL_PROJECTS=/etc/workspaces



