############################################################
# Dockerfile to build Genropy container images
# Based on Ubuntu
############################################################

FROM public.ecr.aws/genropy/genropy
COPY supervisord.conf /root/supervisord.conf
COPY nginx.conf /root/nginx.conf
COPY mime.types /root/mime.types

RUN apk update \
  && apk add py3-psycopg2

