############################################################
# Dockerfile to build Genropy container images
############################################################

FROM python:3.11-slim
RUN apt-get update && apt-get -y full-upgrade &&  apt install -y supervisor nginx python3-psycopg weasyprint && apt-get autoremove -y
RUN pip install --upgrade pip
RUN adduser --group --system --shell /bin/bash --home /home/genro genro
  
RUN mkdir -p /var/lib/nginx/tmp/proxy

RUN chown genro:genro -R /var/lib/nginx /var/log/nginx /var/log/supervisor
RUN touch /var/run/nginx.pid && chown -R genro:genro /var/run/nginx.pid

COPY --chown=genro:genro dockerfiles/genropy/supervisor-genropy.conf /etc/supervisor/conf.d/genropy.conf
COPY --chown=genro:genro dockerfiles/genropy/supervisord.conf /etc/supervisor/
COPY --chown=genro:genro dockerfiles/genropy/nginx.conf /home/genro/nginx.conf
COPY --chown=genro:genro dockerfiles/genropy/mime.types /home/genro/mime.types
COPY --chown=genro:genro dojo_libs/dojo_11 /home/genro/genropy/dojo_libs/dojo_11
COPY --chown=genro:genro gnrjs /home/genro/genropy/gnrjs
COPY --chown=genro:genro gnrpy /home/genro/genropy/gnrpy
COPY --chown=genro:genro projects/gnr_it /home/genro/genropy/projects/gnr_it
COPY --chown=genro:genro projects/gnrcore /home/genro/genropy/projects/gnrcore
COPY --chown=genro:genro resources /home/genro/genropy/resources
COPY --chown=genro:genro webtools /home/genro/genropy/webtools
COPY --chown=genro:genro dockerfiles/genropy/gnrfolder /home/genro/.gnr
RUN rm -fr /home/genro/genropy/.git

WORKDIR /home/genro/genropy/gnrpy
RUN pip install .[developer,pgsql]

WORKDIR /home/genro
ENV GNRLOCAL_PROJECTS=/etc/workspaces

EXPOSE 8080
ENTRYPOINT "supervisord"
