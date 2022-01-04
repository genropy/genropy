############################################################
# Dockerfile to build Genropy container images
# Based on Ubuntu
############################################################

FROM public.ecr.aws/genropy/genropy-pg
COPY supervisord.conf /home/supervisord.conf
COPY nginx.conf /home/nginx.conf
COPY mime.types /home/mime.types

