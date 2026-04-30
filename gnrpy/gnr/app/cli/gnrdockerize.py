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
from gnr.core.gnryaml import GnrYamlBuilder
from gnr.app.pathresolver import PathResolver
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
            
def get_cpu_limit():
    # cgroup v2
    try:
        with open("/sys/fs/cgroup/cpu.max") as f:
            quota, period = f.read().strip().split()
            if quota != "max":
                return max(1, int(int(quota) / int(period)))
    except FileNotFoundError:
        pass

    # cgroup v1 fallback
    try:
        with open("/sys/fs/cgroup/cpu/cpu.cfs_quota_us") as q:
            quota = int(q.read())
        with open("/sys/fs/cgroup/cpu/cpu.cfs_period_us") as p:
            period = int(p.read())
        if quota > 0:
            return max(1, int(quota / period))
    except FileNotFoundError:
        pass

    # fallback (not in k8s or no limits)
    return multiprocessing.cpu_count() or 1

bind = '0.0.0.0:8888'
pidfile = '/home/genro/gunicorn_{instanceName}.pid'
daemon = False
workers = get_cpu_limit()
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
            dockerfile.write("COPY --chown=genro:genro gunicorn.py /home/genro/gunicorn.py\n")
                
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

            dockerfile.write(f"RUN gnr app checkdep --loglevel=debug -v -n -i {self.instance_name}\n")

            dockerfile.write("LABEL {}\n".format(
                " \\ \n\t ".join([f'{k}="{v}"' for k,v in image_labels.items()])
            ))
            dockerfile.write(f'CMD gnr db migrate -u {self.instance_name} && /usr/bin/supervisord\n')
            dockerfile.close()
            logger.info(f"Dockerfile generated at: {self.dockerfile_path}")
            # Ensure to have Docker installed and running
            build_command = ['docker', 'build', '--platform', self.options.architecture,
                             '--progress', self.options.build_progress,
                             '-t', f'{self.image_name}:{version_tag}',
                             self.build_context_dir]
            if self.options.no_pull:
                build_command.insert(2, '--pull=false')
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
            content = self._generate_compose_yaml(version_tag)
            compose_file = f"{self.instance_name}-compose.yml"
            with open(compose_file, "w") as wfp:
                wfp.write(content)
            print(f"Created docker compose file {compose_file}")
            print(f"You can now execute 'docker-compose -f {compose_file} up'")
            print("YMMV, please adjust the generated file accordingly.")

    def _compute_extra_labels(self):
        """Build the optional traefik labels for the app service.

        Returns a list of ``(key, value)`` pairs with native Python types
        (e.g. port numbers stay int) so the YAML emitter can render them
        without spurious quoting. Empty when no fqdn / router is set."""
        if not (self.options.fqdns and self.options.router == 'traefik'):
            return []
        hosts_rule = ' || '.join(f'Host(`{fqdn}`)' for fqdn in self.options.fqdns)
        name = self.instance_name
        return [
            ('traefik.enable', 'true'),
            (f'traefik.http.routers.{name}_web.rule',
             f'({hosts_rule}) && !Path(`/websocket`))'),
            (f'traefik.http.routers.{name}_web.entrypoints', 'http'),
            (f'traefik.http.routers.{name}_web.service', f'{name}_svc_web'),
            (f'traefik.http.services.{name}_svc_web.loadbalancer.server.port', 8888),
            (f'traefik.http.routers.{name}_wsk.rule',
             f'({hosts_rule}) && Path(`/websocket`))'),
            (f'traefik.http.routers.{name}_wsk.entrypoints', 'http'),
            (f'traefik.http.routers.{name}_wsk.service', f'{name}_svc_wsk'),
            (f'traefik.http.services.{name}_svc_wsk.loadbalancer.server.port', 9999),
        ]

    def _generate_compose_yaml(self, version_tag):
        """Dispatch to builder (default) or legacy mako template (``--mako``)."""
        extra_labels = self._compute_extra_labels()
        if self.options.mako:
            return self._compose_via_mako(version_tag, extra_labels)
        return self._compose_via_builder(version_tag, extra_labels)

    def _compose_via_builder(self, version_tag, extra_labels):
        """Build the docker-compose document with GnrYamlBuilder.

        Reads top-down like the compose file itself: volumes, then the db
        service (postgres + healthcheck), then the app service (image,
        traefik labels, ports, db dependency, env, volume mount)."""
        name = self.instance_name

        compose = GnrYamlBuilder()
        compose.child('volumes').set(f'{name}_site', None)

        services = compose.child('services')
        self._compose_db(services.child(f'{name}_db'))
        self._compose_app(services.child(name), version_tag, extra_labels)

        return compose.toYaml(explicit_start=True)

    def _compose_db(self, db):
        name = self.instance_name
        db.set('image', 'postgres:latest')

        env = db.child('environment', kind='sequence')
        env.append('POSTGRES_PASSWORD=S3cret')
        env.append('POSTGRES_USER=genro')
        env.append(f'POSTGRES_DB={name}')

        hc = db.child('healthcheck')
        hc.set('test', ['CMD-SHELL', f'pg_isready -U genro -d {name}'])
        hc.set('interval', '10s')
        hc.set('retries', 5)
        hc.set('start_period', '30s')
        hc.set('timeout', '10s')

    def _compose_app(self, app, version_tag, extra_labels):
        name = self.instance_name
        app.set('image', f'{name}:{version_tag}')

        if extra_labels:
            labels = app.child('labels')
            for key, value in extra_labels:
                labels.set(key, value)

        app.child('ports', kind='sequence').append('8888:8888')

        deps = app.child('depends_on')
        deps.child(f'{name}_db').set('condition', 'service_healthy')

        env = app.child('environment')
        env.set('GNR_DB_IMPLEMENTATION', 'postgres')
        env.set('GNR_DB_HOST', f'${{GNR_DB_HOST:-{name}_db}}')
        env.set('GNR_ROOTPWD', '${GNR_ROOTPWD:-admin}')
        env.set('GNR_DB_USER', '${GNR_DB_USER:-genro}')
        env.set('GNR_DB_PORT', '${GNR_DB_PORT:-5432}')
        env.set('GNR_DB_PASSWORD', '${GNR_DB_PASSWORD:-S3cret}')
        env.set('GNR_LOCALE', 'IT_it')

        app.child('volumes', kind='sequence').append(
            f'{name}_site:/home/genro/site/'
        )

    def _compose_via_mako(self, version_tag, extra_labels):
        """Render the legacy Mako compose template (``--mako`` opt-in).

        Re-flattens the typed ``(key, value)`` pairs into the
        ``"key: value"`` string form that the historical template expects."""
        legacy_labels = [self._format_legacy_label(k, v) for k, v in extra_labels]
        return Template(_LEGACY_COMPOSE_TEMPLATE, strict_undefined=True).render(
            instanceName=self.instance_name,
            version_tag=version_tag,
            extra_labels=legacy_labels,
        )

    @staticmethod
    def _format_legacy_label(key, value):
        if isinstance(value, str) and ' ' in value:
            return f'{key}: "{value}"'
        if isinstance(value, str) and value in ('true', 'false'):
            return f'{key}: "{value}"'
        return f'{key}: {value}'


_LEGACY_COMPOSE_TEMPLATE = """
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
    parser.add_argument('--progress',
                        dest='build_progress',
                        type=str,
                        default='auto',
                        choices=['auto','plain'],
                        help='Docker builder progress')
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
    parser.add_argument('--no-pull',
                        action="store_true",
                        dest="no_pull",
                        help="Avoid pulling remote image, useful for local development")
    parser.add_argument('--router',
                        dest='router',
                        type=str,
                        default='traefik',
                        choices=['traefik'],
                        help="The router to use for deployment")
    parser.add_argument('--mako',
                        action="store_true",
                        dest="mako",
                        help="Use the legacy Mako compose template instead of GnrYamlBuilder")

    parser.add_argument('instance_name')
    
    options = parser.parse_args()

    try:
        builder = MultiStageDockerImageBuilder(options.instance_name,
                                               options=options)
        builder.build_docker_image(version_tag=options.version_tag)
    except Exception as e:
        logger.exception("%s", e)
    
