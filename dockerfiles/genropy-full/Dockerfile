############################################################
# Dockerfile to build Genropy container images
# Based on Ubuntu
############################################################

FROM public.ecr.aws/genropy/genropy
USER root
RUN apk update \
  && apk add supervisor nginx

COPY supervisord.conf /root/supervisord.conf
COPY nginx.conf /root/nginx.conf
COPY mime.types /root/mime.types

USER genro
