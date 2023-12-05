############################################################
# Dockerfile to build Genropy container images
# Based on Ubuntu
############################################################

FROM public.ecr.aws/genropy/genropy
USER root
RUN apk update \
  && apk add supervisor nginx

RUN mkdir -p /var/lib/nginx/tmp/
RUN mkdir -p /var/lib/nginx/tmp/proxy

COPY --chown=genro:genro supervisord.conf /home/genro/supervisord.conf
COPY --chown=genro:genro nginx.conf /home/genro/nginx.conf
COPY --chown=genro:genro mime.types /home/genro/mime.types


RUN chown genro:genro -R /var/lib/nginx 

RUN chown -R genro:genro /var/log/nginx
RUN touch /var/run/nginx.pid && \
        chown -R genro:genro /var/run/nginx.pid

EXPOSE 8080
USER genro


CMD ["supervisord","-c","/home/genro/supervisord.conf"]