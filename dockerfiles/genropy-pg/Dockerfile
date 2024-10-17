############################################################
# Dockerfile to build Genropy-pg container images
# Based on genropy/genropy
############################################################

#FROM public.ecr.aws/genropy/genropy
FROM ghcr.io/genropy/genropy:testing
RUN apt update \
  && apt install -y python3-psycopg2