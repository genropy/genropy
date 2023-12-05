############################################################
# Dockerfile to build Genropy container images
# Based on Ubuntu
############################################################

FROM public.ecr.aws/genropy/genropy
USER root
RUN pip install -U supervisor
COPY --chown=genro:genro supervisord.conf /home/genro/supervisord.conf
EXPOSE 8080
USER genro

CMD ["supervisord","-c","/home/genro/supervisord.conf"]