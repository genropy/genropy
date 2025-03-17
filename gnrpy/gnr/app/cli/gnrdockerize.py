#!/usr/bin/env python
# encoding: utf-8

"""
Create a Dockerfile for an instance, starting from a specific configuration file,
and build the finale image
"""
import shutil
import tempfile
import datetime
import os
import subprocess
import xml.etree.ElementTree as ET

from gnr.core.cli import GnrCliArgParse
from gnr.app.gnrapp import GnrApp
from gnr.app import logger

description = "Create a Docker image for the instance"

class MultiStageDockerImageBuilder:
    def __init__(self, instance, options):
        self.instance = instance
        self.options = options
        self.config_file = os.path.join(self.instance.instanceFolder, "build.xml")
        self.dependencies = self.load_config()

    def load_config(self):
        """Load and parse the XML configuration file."""
        tree = ET.parse(self.config_file)
        root = tree.getroot()
        return root

    def get_docker_images(self):
        """Get a list of Docker image dependencies."""
        docker_images = []
        for image_elem in self.dependencies.find('docker_images').findall('image'):
            image = {
                'name': image_elem.find('name').text,
                'tag': image_elem.find('tag').text,
                'description': image_elem.find('description').text if image_elem.find('description') is not None else 'No description'
            }
            docker_images.append(image)
        return docker_images

    def get_git_repositories(self):
        """Get a list of Git repository dependencies."""
        git_repositories = []
        for repo_elem in self.dependencies.find('git_repositories').findall('repository'):
            repo = {
                'url': repo_elem.find('url').text,
                'branch_or_commit': repo_elem.find('branch_or_commit').text if repo_elem.find('branch_or_commit') is not None else 'master',
                'description': repo_elem.find('description').text if repo_elem.find('description') is not None else 'No description'
            }
            git_repositories.append(repo)

        # Include the instance repository too
        start_build_dir = os.getcwd()
        os.chdir(self.instance.instanceFolder)
        main_repo_url = subprocess.check_output(["git", "remote", "get-url", "origin"]).decode().strip()
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
        os.chdir(start_build_dir)
        code_repo = {
            'url': main_repo_url,
            'branch_or_commit': commit,
            'description': self.instance.instanceName
            }
        
        git_repositories.append(code_repo)
        return git_repositories

    def build_docker_image(self, version_tag="latest"):
        """
        Generate a multi-stage Dockerfile that clones and copies
        repositories from multiple Docker images.
        """
        docker_images = self.get_docker_images()
        git_repositories = self.get_git_repositories()
        now = datetime.datetime.now(datetime.UTC)
        image_labels = {"gnr_app_dockerize_on": str(now)}
        entry_dir = os.getcwd()
        
        with tempfile.TemporaryDirectory(dir=os.getcwd()) as build_context_dir:
            os.chdir(build_context_dir)
            self.dockerfile_path = os.path.join(build_context_dir, "Dockerfile")
            with open(self.dockerfile_path, 'w') as dockerfile:
                dockerfile.write(f"# Docker image for instance {self.instance.instanceName}\n")
                dockerfile.write(f"# Dockerfile builded on {now}\n\n")
                # Genropy image, which is our base image
                dockerfile.write("FROM ghcr.io/genropy/genropy:develop as build_stage\n")
                dockerfile.write("WORKDIR /home/genro/genropy_projects\n")
                dockerfile.write("RUN apt-get update && apt-get install -y git\n")
                dockerfile.write("USER genro\n\n")
            
                for idx, repo in enumerate(git_repositories, start=1):
                
                    repo_name = repo['url'].split("/")[-1].replace(".git", "")
                    logger.info(f"Checking repository {repo_name} at {repo['url']}")
                    
                    subprocess.run(["git", "clone", repo['url'], repo_name],
                                   check=True,
                                   stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL,
                                   )
                    os.chdir(os.path.join(build_context_dir, repo_name))
                    subprocess.run(["git", "checkout", repo['branch_or_commit']],
                                   check=True,
                                   stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL,
                                   )
                    commit = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
                    if commit == repo['branch_or_commit']:
                        image_labels[f'git:{repo_name}'] = f"@{commit}"
                    else:
                        image_labels[f'git:{repo_name}'] = f"{repo['branch_or_commit']}@{commit}"
                    shutil.rmtree(".git")
                    # go back to original build directory
                    os.chdir(build_context_dir)
                    docker_clone_dir = f"/home/genro/genropy_project/{repo_name}"
                    dockerfile.write(f"# {repo['description']}\n")
                    dockerfile.write(f"COPY --chown=genro:genro {repo_name} /home/genro/genropy_projects/{repo_name}\n")

                # Copy repositories from each build stage into the final image
                for i in range(1, len(docker_images) + 1):
                    for idx, repo in enumerate(git_repositories):
                        dockerfile.write(f"COPY --from=build_stage{i} /{repo['url'].split('/')[-1]} /app/{repo['url'].split('/')[-1]}\n")
                        
                dockerfile.write("\n# Final customizations\n")
                gunicorn_template = """
import multiprocessing                                                                                                                  
                                                                                                                                        
bind = '0.0.0.0:8888'                                                                                                                   
pidfile = '/home/genro/gunicorn_{instanceName}.pid'                                                                                            
daemon = False                                                                                                                          
workers = multiprocessing.cpu_count()                                                                                                   
threads = 8                                                                                                                             
loglevel = 'error'                                                                                                                      
chdir = '/home/genro/genropy_projects/sandbox/instances/{instanceName}'                                                                      
reload = False                                                                                                                          
capture_output = True                                                                                                                   
max_requests = 600                                                                                                                      
max_requests_jitter = 50                                                                                                                
timeout = 1800                                                                                                                          
graceful_timeout = 600      
                """
                with open("gunicorn.py", "w") as wfp:
                    wfp.write(gunicorn_template.format(instanceName=self.instance.instanceName))
                dockerfile.write(f"COPY --chown=genro:genro gunicorn.py /home/genro/gunicorn.py\n")
                
                supervisor_template = """
[program:dbsetup]                                                                                                                       
autorestart=unexpected                                                                                                                  
startsecs = 0                                                                                                                           
exitcodes = 0                                                                                                                           
command=gnr db setup {instanceName}
                                                                                                                                        
[program:wsgiserver]                                                                                                                    
command=gunicorn -c /home/genro/gunicorn.py root                                                                                        
                                                                                                                                        
[program:gnrasync]                                                                                                                      
command=gnrasync -p 9999 {instanceName}                                                                                                      
                                                                                                                                        
[program:gnrtaskscheduler]                                                                                                              
command=gnrtaskscheduler {instanceName}
                                                                                                                                        
[program:gnrtaskworker]                                                                                                                 
command=gnrtaskworker {instanceName}
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
                image_push = f"{self.instance.instanceName}:{version_tag}"
                image_push_url = f'{self.options.registry}/{self.options.username}/{image_push}'
                logger.info(f"Tagging image {image_push} to {image_push_url}")
                subprocess.run(['docker','tag', image_push, image_push_url])
                logger.info(f"Pushing image to {image_push_url}")
                subprocess.run(['docker', 'push', image_push_url])
                
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
    
