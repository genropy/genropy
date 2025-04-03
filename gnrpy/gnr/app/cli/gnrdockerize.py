#!/usr/bin/env python
# encoding: utf-8

"""
Create a Dockerfile for an instance, starting from a specific configuration file,
and build the finale image
"""
import sys
import shutil
import tempfile
import datetime
import os
import subprocess

from gnr.core.cli import GnrCliArgParse
from gnr.core.gnrbag import Bag
from gnr.app.gnrapp import GnrApp
from gnr.app import logger

description = "Create a Docker image for the instance"
gnr_cli_hide = True

class MultiStageDockerImageBuilder:
    def __init__(self, instance, options):
        self.instance = instance
        self.options = options

        # check for required executables
        require_executables = ['git','docker']
        missing_execs = []
        for executable in require_executables:
            if shutil.which(executable) is None:
                missing_execs.append(executable)

        if missing_execs:
            logger.error("Missing executables: %s - please install", ", ".join(missing_execs))
            sys.exit(1)

        self.main_repo_name = ""
        
        # check if build configuration is present - in the future, the configuration
        # could be passed as Bag to the constructor
        self.config_file = os.path.join(self.instance.instanceFolder, "build.xml")

        logger.debug("Build configuration file: %s", self.config_file)

        if not os.path.exists(self.config_file):
            # generate a build configuration analyzing the instance
            logger.warning(f"Build file configuration not found, creating one from current status")
            self._create_build_config()
        else:
            logger.info("Found build configuration in instance folder")
            
        self.config = self.load_config()

    def _create_build_config(self):
        config_bag = Bag()
        dependencies = Bag()
        config_bag.setItem('dependencies', dependencies)
        
        # search for git repos
        git_repos_bag= Bag()
        for package, obj in self.instance.packages.items():
            url = self._get_git_url_from_path(obj.packageFolder)

            if "genropy/genropy" in url:
                continue
            branch_or_commit = self._get_git_commit_from_path(obj.packageFolder)
            description = url.split('/')[-1].replace(".git","")
            logger.debug("Package %s is using git remote %s on branch/commit %s", obj.packageFolder, url, branch_or_commit)
            git_repos_bag.setItem(description, None,
                                  url=url,
                                  branch_or_commit=branch_or_commit,
                                  description=description)

        dependencies.setItem("git_repositories", git_repos_bag)
        with open(self.config_file, "w") as wfp:
            wfp.write(config_bag.toXml())

    def load_config(self):
        """Load and parse the XML configuration file."""

        b = Bag(self.config_file)
        return Bag(self.config_file)

    def get_docker_images(self):
        """Get a list of Docker image dependencies."""
        docker_images = []
        
        for i in self.config['dependencies'].get('docker_images', []):
            image_conf = i.__dict__['_value']
            image = {
                'name': image_conf.get("name"),
                'tag': image_conf.get("tag"),
                'description': image_conf.get('description', "No description")
            }
            docker_images.append(image)
        return docker_images

    def _get_git_url_from_path(self, path):
        url = subprocess.check_output(["git", "remote", "get-url", "origin"], cwd=path).decode().strip()
        return url
    
    def _get_git_commit_from_path(self, path):
        url = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=path).decode().strip()
        return url
    
    def _get_git_branch_from_path(self, path):
        url = subprocess.check_output(["git", "branch", "--show-current"], cwd=path).decode().strip()
        return url
    
    def _get_git_repo_name_from_url(self, url):
        return url.split("/")[-1].replace(".git", "")
    
    def get_git_repositories(self):
        """Get a list of Git repository dependencies."""
        git_repositories = []
        git_config = self.config.get("dependencies", {}).get("git_repositories", {})
        if isinstance(git_config, Bag):
            for r in git_config:
                repo_conf = r.attr
                repo = {
                    'url': repo_conf.get('url'),
                    'branch_or_commit': repo_conf.get('branch_or_commit', 'master'),
                    'subfolder': repo_conf.get("subfolder", None),
                    'description': repo_conf.get("description", "No description")
                }
                git_repositories.append(repo)

        # Include the instance repository too
        start_build_dir = os.getcwd()
        os.chdir(self.instance.instanceFolder)
        main_repo_url = self._get_git_url_from_path(self.instance.instanceFolder)
        # get the repo name, needed for gunicorn/supervisor templates
        self.main_repo_name = self._get_git_repo_name_from_url(main_repo_url)
        commit = self._get_git_commit_from_path(self.instance.instanceFolder)
        os.chdir(start_build_dir)
        code_repo = {
            'url': main_repo_url,
            'branch_or_commit': commit,
            'description': self.instance.instanceName,
            'subfolder': None
            }
        
        git_repositories.append(code_repo)
        logger.debug("Found git repositories: %s", git_repositories)
        return git_repositories

    def build_docker_image(self, version_tag="latest"):
        """
        Generate a multi-stage Dockerfile that clones and copies
        repositories from multiple Docker images.
        """
        git_repositories = self.get_git_repositories()
        now = datetime.datetime.now(datetime.UTC)
        image_labels = {"gnr_app_dockerize_on": str(now)}
        entry_dir = os.getcwd()
        build_context_dir = tempfile.mkdtemp(dir=os.getcwd())
        if True:
            os.chdir(build_context_dir)
            self.dockerfile_path = os.path.join(build_context_dir, "Dockerfile")
            with open(self.dockerfile_path, 'w') as dockerfile:
                dockerfile.write(f"# Docker image for instance {self.instance.instanceName}\n")
                dockerfile.write(f"# Dockerfile builded on {now}\n\n")
                # Genropy image, which is our base image
                dockerfile.write("FROM ghcr.io/genropy/genropy:develop as build_stage\n")
                dockerfile.write("WORKDIR /home/genro/genropy_projects\n")
                dockerfile.write("USER genro\n\n")
                dockerfile.write('ENV PATH="/home/genro/.local/bin:$PATH"\n')
            
                for idx, repo in enumerate(git_repositories, start=1):

                    repo_name = repo['url'].split("/")[-1].replace(".git", "")
                    logger.info(f"Checking repository {repo_name} at {repo['url']}")
                    
                    result = subprocess.run(["git", "clone", repo['url'], repo_name],
                                            check=True,
                                            capture_output=True
                                            )
                    if result.returncode == 0:
                        logger.debug("Git clone for %s went ok", repo['url'])
                    else:
                        logger.error("Error cloning %s: %s", repo['url'], result.stderr)
                        
                    os.chdir(os.path.join(build_context_dir, repo_name))
                    result = subprocess.run(["git", "checkout", repo['branch_or_commit']],
                                   check=True,
                                   capture_output=True
                                   )
                    if result.returncode == 0:
                        logger.debug("Git checkout for branch %s went ok", repo['branch_or_commit'])
                    else:
                        logger.error("Error checking out %s: %s", repo['branch_or_commit'], result.stderr)
                        
                    commit = self._get_git_commit_from_path(".")
                    if commit == repo['branch_or_commit']:
                        image_labels[f'git:{repo_name}'] = f"@{commit}"
                    else:
                        image_labels[f'git:{repo_name}'] = f"{repo['branch_or_commit']}@{commit}"

                    image_labels[f'git:{repo_name}:url'] = "{http_repo_url}/commit/{commit}".format(
                        # awful hack to get https URL on github if the repository is cloned via ssh
                        http_repo_url=repo['url'].replace("git@", "https://").replace(".git","").replace("github.com:", "github.com/"),
                        commit=commit
                    )
                    
                    shutil.rmtree(".git")
                    # go back to original build directory
                    os.chdir(build_context_dir)
                    docker_clone_dir = f"/home/genro/genropy_project/{repo_name}"
                    dockerfile.write(f"# {repo['description']}\n")
                    if repo['subfolder']:
                        dockerfile.write(f"COPY --chown=genro:genro {repo_name}/{repo['subfolder']} /home/genro/genropy_projects/{repo['subfolder']}\n")
                    else:
                        dockerfile.write(f"COPY --chown=genro:genro {repo_name} /home/genro/genropy_projects/{repo_name}\n")

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
                    wfp.write(gunicorn_template.format(instanceName=self.instance.instanceName,
                                                       main_repo_name=self.main_repo_name))
                dockerfile.write(f"COPY --chown=genro:genro gunicorn.py /home/genro/gunicorn.py\n")
                
                supervisor_template = """
[supervisord]
nodaemon = true
                
[program:dbsetup]
autorestart=unexpected
startsecs = 0
exitcodes = 0
command=gnr db setup {instanceName}
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0


[program:httpserver]
command=gunicorn -c /home/genro/gunicorn.py root
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0

[program:gnrasync]
command=gnr app async -p 9999 {instanceName}
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0

[program:gnrtaskscheduler]
command=gnr web taskscheduler {instanceName}
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0

[program:gnrtaskworker]
command=gnr web taskworker {instanceName}
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
                """
                with open("supervisord.conf", "w") as wfp:
                    wfp.write(supervisor_template.format(instanceName=self.instance.instanceName))
                dockerfile.write(f"COPY --chown=genro:genro supervisord.conf /etc/supervisor/conf.d/{self.instance.instanceName}-supervisor.conf\n")

                dockerfile.write(f"RUN gnr app checkdep -i {self.instance.instanceName}\n")
                dockerfile.write("LABEL {}\n".format(
                    " \\ \n\t ".join([f'{k}="{v}"' for k,v in image_labels.items()])
                ))
                dockerfile.write('ENTRYPOINT ["/usr/bin/supervisord"]\n')
                dockerfile.close()
                logger.info(f"Dockerfile generated at: {self.dockerfile_path}")
                # Ensure to have Docker installed and running
                build_command = ['docker', 'build', '-t',
                                 f'{self.instance.instanceName}:{version_tag}',
                                 build_context_dir]
                subprocess.run(build_command, check=True)
                logger.info("Docker image built successfully.")
                os.chdir(entry_dir)
                
            if self.options.push:
                # push the newly created image to the registry
                image_push = f"{self.instance.instanceName}:{version_tag}"
                image_push_url = f'{self.options.registry}/{self.options.username}/{image_push}'
                logger.info(f"Tagging image {image_push} to {image_push_url}")
                subprocess.run(['docker','tag', image_push, image_push_url])
                logger.info(f"Pushing image {image_push_url}")
                subprocess.run(['docker', 'push', image_push_url])
        if self.options.keep_temp:
            print(f"The build directory {build_context_dir} has NOT been removed")
        else:
            shutil.rmtree(build_context_dir)
            
def main():
    parser = GnrCliArgParse(description=description)
    parser.add_argument('-t', '--tag',
                        dest="version_tag",
                        help="The image version tag",
                        type=str,
                        default="latest")
    parser.add_argument('-p', '--push',
                        dest="push",
                        action="store_true",
                        help="Push the image into the registry")
    parser.add_argument('--keep-temp',
                        action="store_true",
                        dest="keep_temp",
                        help="Keep intermediate data for debugging the image build")
    parser.add_argument('-r', '--registry',
                        dest="registry",
                        type=str,
                        default="ghcr.io",
                        help="The registry where to push the image")
    parser.add_argument('-u', '--username',
                        dest="username",
                        type=str,
                        default="softwellsrl",
                        help="The registry username where to push the image")
    
    parser.add_argument('instance_name')
    
    options = parser.parse_args()

    try:
        instance = GnrApp(options.instance_name)
        builder = MultiStageDockerImageBuilder(instance, options=options)
        builder.build_docker_image(version_tag=options.version_tag)
    except Exception as e:
        logger.exception("%s", e)
    
