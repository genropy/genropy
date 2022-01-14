############################################################
# Dockerfile to build Genropy container images
# Based on Ubuntu
############################################################

FROM public.ecr.aws/genropy/genropy-pg
COPY supervisord.conf /root/supervisord.conf
COPY nginx.conf /root/nginx.conf
COPY mime.types /root/mime.types

