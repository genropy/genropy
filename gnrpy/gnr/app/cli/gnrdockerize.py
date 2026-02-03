#!/usr/bin/env python
# encoding: utf-8

"""
Create a Dockerfile for an instance, starting from a specific configuration file,
and build the final image
"""
import atexit
import sys
import shutil
import tempfile
import datetime
import os
import subprocess

from mako.template import Template

from gnr.core.cli import GnrCliArgParse
from gnr.app.gnrdeploy import PathResolver
from gnr.dev.builder import GnrProjectBuilder
from gnr.app import logger

description = "Create a Docker image for the instance"

class MultiStageDockerImageBuilder:
    def __init__(self, instance_name, options):
        self.instance_name = instance_name
        self.instance_folder = PathResolver().instance_name_to_path(self.instance_name)
        self.image_name = options.image_name or self.instance_name
        self.options = options
        self.builder = GnrProjectBuilder(self.instance_name)

        # check for required executables
        require_executables = ['docker']
        missing_execs = []
        for executable in require_executables:
            if shutil.which(executable) is None:
                missing_execs.append(executable)

        if missing_execs:
            logger.error("Missing executables: %s - please install", ", ".join(missing_execs))
            sys.exit(1)

        self.main_repo_name = ""
        
        self.config = self.builder.load_config(generate=options.build_generate)
        self.build_context_dir = tempfile.mkdtemp(dir=os.getcwd())
        atexit.register(self.cleanup_build_dir)
        
    def cleanup_build_dir(self):
        if self.options.keep_temp:
            logger.warning(f"As requested, the build directory {self.build_context_dir} has NOT been removed")
        else:
            shutil.rmtree(self.build_context_dir)

    def get_docker_images(self):
        """Get a list of Docker image dependencies."""
        docker_images = []
        
        for image_conf in self.config['dependencies'].get('docker_images', []):
            image = {
                'name': image_conf.get("name"),
                'tag': image_conf.get("tag"),
                'description': image_conf.get('description', "No description")
            }
            docker_images.append(image)
        return docker_images

    def build_docker_image(self, version_tag="latest"):
        """
        Generate a multi-stage Dockerfile that clones and copies
        repositories from multiple Docker images.
        """
        git_repositories = self.builder.git_repositories()
        now = datetime.datetime.now(datetime.UTC)
        image_labels = {"gnr_app_dockerize_on": str(now)}
        entry_dir = os.getcwd()

        main_repo_url = self.builder.git_url_from_path(self.instance_folder)
        self.main_repo_name = self.builder.git_repo_name_from_url(main_repo_url)
        
        os.chdir(self.build_context_dir)
        self.dockerfile_path = os.path.join(self.build_context_dir, "Dockerfile")
        with open(self.dockerfile_path, 'w') as dockerfile:
            dockerfile.write(f"# Docker image for instance {self.instance_name}\n")
            dockerfile.write(f"# Dockerfile builded on {now}\n\n")
            # Genropy image, which is our base image
            base_image_tag = self.options.bleeding and "develop" or "latest"
            dockerfile.write(f"FROM ghcr.io/genropy/genropy:{base_image_tag} as build_stage\n")
            dockerfile.write("WORKDIR /home/genro/genropy_projects\n")
            dockerfile.write("USER genro\n\n")
            dockerfile.write('ENV PATH="/home/genro/.local/bin:$PATH"\n')
            dockerfile.write('ENV GENRO_GNRFOLDER="/home/genro/.gnr/"\n')
            
            self.builder.checkout_project(dest_dir=".")
                
            for idx, repo in enumerate(git_repositories, start=1):
                repo_name = self.builder.git_repo_name_from_url(repo['url'])
                    
                repo_path = os.path.join(self.build_context_dir, repo_name)

                    
                commit = self.builder.git_commit_from_path(repo_path)
                    
                if commit == repo['branch_or_commit']:
                    image_labels[f'git:{repo_name}'] = f"@{commit}"
                else:
                    image_labels[f'git:{repo_name}'] = f"{repo['branch_or_commit']}@{commit}"
                    
                image_labels[f'git:{repo_name}:url'] = "{http_repo_url}/commit/{commit}".format(
                    # awful hack to get https URL on github if the repository is cloned via ssh
                    http_repo_url=repo['url'].replace("git@", "https://").replace(".git","").replace("github.com:", "github.com/"),
                    commit=commit
                )
                
                os.chdir(repo_path)
                # remove the git folder - ignore errors
                # because the downloaded repo could be an archive rather than
                # a clone
                shutil.rmtree(".git", ignore_errors=True)
                # go back to original build directory
                os.chdir(self.build_context_dir)
                
                docker_clone_dir = f"/home/genro/genropy_project/{repo_name}"
                dockerfile.write(f"# {repo['description']}\n")
                site_folder = f"/home/genro/genropy_projects/{repo_name}/instances/{self.instance_name}/site"
                if repo['subfolder']:
                    site_folder = f"/home/genro/genropy_projects/{repo['subfolder']}/instances/{self.instance_name}/site"
                    dockerfile.write(f"COPY --chown=genro:genro {repo_name}/{repo['subfolder']} /home/genro/genropy_projects/{repo['subfolder']}\n")
                else:

                    dockerfile.write(f"COPY --chown=genro:genro {repo_name} /home/genro/genropy_projects/{repo_name}\n")

            dockerfile.write(f"RUN ln -s {site_folder} /home/genro/site\n")
            dockerfile.write("EXPOSE 8888/tcp 9999/tcp\n")
            
            dockerfile.write("\n# Final customizations\n")
            gunicorn_template = """
import multiprocessing
bind = '0.0.0.0:8888'
pidfile = '/home/genro/gunicorn_{instanceName}.pid'
daemon = False
workers = multiprocessing.cpu_count()
threads = 8
loglevel = 'error'
chdir = '/home/genro/genropy_projects/{main_repo_name}/instances/{instanceName}'
reload = False
capture_output = True
max_requests = 600
max_requests_jitter = 50
timeout = 1800
graceful_timeout = 600      
                """
            with open("gunicorn.py", "w") as wfp:
                wfp.write(gunicorn_template.format(instanceName=self.instance_name,
                                                       main_repo_name=self.main_repo_name))
            dockerfile.write(f"COPY --chown=genro:genro gunicorn.py /home/genro/gunicorn.py\n")
                
            supervisor_template = """
[supervisord]
nodaemon = true
                
[program:dbsetup]
priority=1
autorestart=unexpected
startsecs = 0
exitcodes = 0
command=gnr db migrate -u {instanceName}
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0


[program:httpserver]
priority=50
command=gnr web serveprod {instanceName} -c /home/genro/gunicorn.py
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0

[program:gnrasync]
priority=999
command=gnr app async -p 9999 {instanceName}
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0

[program:gnrtaskscheduler]
priority=999
command=gnr web taskscheduler {instanceName}
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0

[program:gnrtaskworker]
priority=999
command=gnr web taskworker {instanceName}
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
                """
            with open("supervisord.conf", "w") as wfp:
                wfp.write(supervisor_template.format(instanceName=self.instance_name))
                    
            dockerfile.write(f"COPY --chown=genro:genro supervisord.conf /etc/supervisor/conf.d/{self.instance_name}-supervisor.conf\n")

            dockerfile.write(f"RUN gnr app checkdep -n -i {self.instance_name}\n")

            dockerfile.write("LABEL {}\n".format(
                " \\ \n\t ".join([f'{k}="{v}"' for k,v in image_labels.items()])
            ))
            dockerfile.write(f'CMD gnr db migrate -u {self.instance_name} && /usr/bin/supervisord\n')
            dockerfile.close()
            logger.info(f"Dockerfile generated at: {self.dockerfile_path}")
            # Ensure to have Docker installed and running
            build_command = ['docker', 'build', '--platform', self.options.architecture,
                             '-t', f'{self.image_name}:{version_tag}',
                             self.build_context_dir]
            subprocess.run(build_command, check=True)
            logger.info("Docker image built successfully.")
            os.chdir(entry_dir)
                
        if self.options.push:
            # push the newly created image to the registry
            image_push = f"{self.image_name}:{version_tag}"
            image_push_url = f'{self.options.registry}/{self.options.username}/{image_push}'
            logger.info(f"Tagging image {image_push} to {image_push_url}")
            subprocess.run(['docker','tag', image_push, image_push_url])
            logger.info(f"Pushing image {image_push_url}")
            subprocess.run(['docker', 'push', image_push_url])

        # docker compose conf file
        if self.options.compose:
            extra_labels = []
            if self.options.fqdns and self.options.router == 'traefik':
                hosts_rule = " || ".join([f"Host(`{fqdn}`)" for fqdn in self.options.fqdns])
                extra_labels.extend([
                    'traefik.enable: "true"',
                    f'traefik.http.routers.{self.instance_name}_web.rule: "({hosts_rule}) && !Path(`/websocket`))"',
                    f'traefik.http.routers.{self.instance_name}_web.entrypoints: http',
                    f'traefik.http.routers.{self.instance_name}_web.service: {self.instance_name}_svc_web',
                    f'traefik.http.services.{self.instance_name}_svc_web.loadbalancer.server.port: 8888',
                    f'traefik.http.routers.{self.instance_name}_wsk.rule: "({hosts_rule}) && Path(`/websocket`))"',
                    f'traefik.http.routers.{self.instance_name}_wsk.entrypoints: http',
                    f'traefik.http.routers.{self.instance_name}_wsk.service: {self.instance_name}_svc_wsk',
                    f'traefik.http.services.{self.instance_name}_svc_wsk.loadbalancer.server.port: 9999'
                ])
                    
            compose_template = """
---
# Docker compose file for instance ${instanceName}:${version_tag}

volumes:
  ${instanceName}_site:

services:
  ${instanceName}_db:
    image: postgres:latest
    environment:
      - POSTGRES_PASSWORD=S3cret
      - POSTGRES_USER=genro
      - POSTGRES_DB=${instanceName}
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U genro -d ${instanceName}"]
      interval: 10s
      retries: 5
      start_period: 30s
      timeout: 10s
  ${instanceName}:
    image: ${instanceName}:${version_tag}
    % if extra_labels:
    labels:
    % for l in extra_labels:
      ${l}
    % endfor
    % endif:
    ports:
      - "8888:8888"
    depends_on:
      ${instanceName}_db:
        condition: service_healthy
    environment:
      GNR_DB_IMPLEMENTATION : "postgres"
      GNR_DB_HOST : ${r"${GNR_DB_HOST:-" + instanceName + "_db}"}
      GNR_ROOTPWD : ${r"${GNR_ROOTPWD:-admin}"}
      GNR_DB_USER : ${r"${GNR_DB_USER:-genro}"}
      GNR_DB_PORT : ${r"${GNR_DB_PORT:-5432}"}
      GNR_DB_PASSWORD: ${r"${GNR_DB_PASSWORD:-S3cret}"}
      GNR_LOCALE: "IT_it"
    volumes:
      - ${instanceName}_site:/home/genro/site/
                
                """
            compose_template_file = f"{self.instance_name}-compose.yml"
            with open(compose_template_file, "w") as wfp:
                t = Template(compose_template, strict_undefined=True)
                wfp.write(t.render(instanceName=self.instance_name,
                                   version_tag=version_tag,
                                   extra_labels=extra_labels))
                print(f"Created docker compose file {compose_template_file}")
                print(f"You can now execute 'docker-compose -f {compose_template_file} up'")
                print("YMMV, please adjust the generated file accordingly.")
                    
def main():
    parser = GnrCliArgParse(description=description)
    parser.add_argument('-c','--compose',
                        action="store_true",
                        dest="compose",
                        help="Generate a docker compose file for the created image")
    parser.add_argument('-f', '--fqdn',
                        dest="fqdns",
                        action='append',
                        type=str,
                        default=[],
                        help="One (or more) FQDN of the site deployment")
    parser.add_argument('-n', '--name',
                        dest="image_name",
                        help="The image name (default to instance name)",
                        type=str)
    parser.add_argument('-p', '--push',
                        dest="push",
                        action="store_true",
                        help="Push the image into the registry")
    parser.add_argument('-r', '--registry',
                        dest="registry",
                        type=str,
                        default="ghcr.io",
                        help="The registry where to push the image")
    parser.add_argument('-a', '--arch',
                        dest="architecture",
                        type=str,
                        default="linux/amd64",
                        help="The image architecture/platform to be built for")
    parser.add_argument('-t', '--tag',
                        dest="version_tag",
                        help="The image version tag",
                        type=str,
                        default="latest")
    parser.add_argument('-u', '--username',
                        dest="username",
                        type=str,
                        default="softwellsrl",
                        help="The registry username where to push the image")
    parser.add_argument('--bleeding',
                        action="store_true",
                        dest="bleeding",
                        help="Use Genropy from latest develop image")
    parser.add_argument('--build-gen',
                        action="store_true",
                        dest="build_generate",
                        help="Force the automatically creation of the build.json file")
    parser.add_argument('--keep-temp',
                        action="store_true",
                        dest="keep_temp",
                        help="Keep intermediate data for debugging the image build")
    parser.add_argument('--router',
                        dest='router',
                        type=str,
                        default='traefik',
                        choices=['traefik'],
                        help="The router to use for deployment")
    
    parser.add_argument('instance_name')
    
    options = parser.parse_args()

    try:
        builder = MultiStageDockerImageBuilder(options.instance_name,
                                               options=options)
        builder.build_docker_image(version_tag=options.version_tag)
    except Exception as e:
        logger.exception("%s", e)
    
