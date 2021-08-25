# grown-up modules
import compose.cli.command
import docker
import os
import logging

# local modules
import context
import install
import execute

# TODO: Way to know the absolute path of the thing that is actually running (this script)
#script_path = os.path.dirname(os.path.realpath(__file__))

class execution_context:
    def __init__(self, args):
        self.platform_name, self.platform_version = context.platform_name_and_version(args.platform)
        self.database_name, self.database_version = context.database_name_and_version(args.database)

        self.project_name = '-'.join([self.platform_name,
                                      self.platform_version,
                                      self.database_name,
                                      self.database_version])

        if args.job_name:
            self.job_name = '_'.join([args.job_name, self.project_name])
        else:
            import uuid
            # TODO: use timestamps, also
            self.job_name = '_'.join([str(uuid.uuid4()), self.project_name])

        if args.output_directory:
            self.output_directory = os.path.join(os.path.abspath(args.output_directory), self.job_name)
        else:
            import tempfile
            self.output_directory = os.path.join(tempfile.mkdtemp(prefix=self.project_name), self.job_name)

def wait_for_setup_to_finish(c, timeout_in_seconds):
    import time

    FLAG_FILE = '/var/lib/irods/setup_complete'

    logging.info('waiting for iRODS to finish setting up [{}]'.format(c.name))

    start_time = time.time()
    now = start_time

    while now - start_time < timeout_in_seconds:
        if execute.execute_command(c, 'stat {}'.format(FLAG_FILE)) == 0:
            logging.info('iRODS has been set up (waited [{}] seconds)'.format(str(now - start_time)))
            return

        time.sleep(1)
        now = time.time()

    raise RuntimeError('timed out while waiting for iRODS to finish setting up')

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST or not os.path.isdir(path):
            raise

def configure_irods_testing(docker_client, containers):
    # Make sure univMSS interface is configured for testing
    path_to_univmss_script = os.path.join('/var', 'lib', 'irods', 'msiExecCmd_bin', 'univMSSInterface.sh')
    chown_msiexec_directory = 'chown irods:irods {}'.format(os.path.dirname(path_to_univmss_script))
    copy_from_template = 'cp {0}.template {0}'.format(path_to_univmss_script)
    remove_template_from_commands = 'sed -i \"s/template-//g\" {}'.format(path_to_univmss_script)
    make_script_executable = 'chmod 544 {}'.format(path_to_univmss_script)

    for container in containers:
        if context.is_catalog_database_container(container): continue

        c = docker_client.containers.get(container.name)
        if execute.execute_command(c, chown_msiexec_directory) is not 0:
            raise RuntimeError('failed to change ownership to msiExecCmd_bin')
        if execute.execute_command(c, copy_from_template, user='irods', workdir='/var/lib/irods') is not 0:
            raise RuntimeError('failed to copy univMSSInterface.sh template file')
        if execute.execute_command(c, remove_template_from_commands, user='irods', workdir='/var/lib/irods') is not 0:
            raise RuntimeError('failed to modify univMSSInterface.sh template file')
        if execute.execute_command(c, make_script_executable, user='irods', workdir='/var/lib/irods') is not 0:
            raise RuntimeError('failed to change permissions on univMSSInterface.sh')

if __name__ == "__main__":
    import argparse
    import logs

    parser = argparse.ArgumentParser(description='Run iRODS tests in a consistent environment.')
    parser.add_argument('commands', metavar='COMMANDS', nargs='+',
                        help='Space-delimited list of commands to be run')
    parser.add_argument('--run-on-container', '-t', metavar='TARGET_CONTAINER', dest='run_on', type=str, default='irods-catalog-provider',
                        help='The name of the container on which the command will run')
    parser.add_argument('--irods-setup-wait-time', '-w', metavar='SETUP_TIMEOUT_IN_SECONDS', dest='setup_timeout', type=int, default=30,
                        help='How many seconds to wait before timing out while waiting on iRODS server to be set up.')
    parser.add_argument('--output-directory', '-o', metavar='FULLPATH_TO_DIRECTORY_FOR_OUTPUT', dest='output_directory', type=str,
                        help='Full path to local directory for output from execution.')
    parser.add_argument('--os-platform-tag', '-p', metavar='OS_PLATFORM_IMAGE_TAG', dest='platform', type=str, default='ubuntu:18.04',
                        help='The tag of the base Docker image to use (e.g. centos:7)')
    parser.add_argument('--database-tag', '-d', metavar='DATABASE_IMAGE_TAG', dest='database', type=str, default='postgres:10.12',
                        help='The tag of the database container to use (e.g. postgres:10.12')
    parser.add_argument('--job-name', '-j', metavar='JOB_NAME', dest='job_name', type=str,
                        help='Name of the test run')
    parser.add_argument('--install-packages-from', '-i', metavar='PATH_TO_DIRECTORY_WITH_PACKAGES', dest='package_directory', type=str,
                        help='Full path to local directory which contains packages to be installed on iRODS containers.')
    parser.add_argument('--verbose', '-v', dest='verbosity', action='count', default=1,
                        help='Increase the level of output to stdout. CRITICAL and ERROR messages will always be printed.')

    args = parser.parse_args()

    docker_client = docker.from_env()
    ctx = execution_context(args)

    mkdir_p(ctx.output_directory)

    logs.configure(args.verbosity, os.path.join(ctx.output_directory, 'script_output.log'))

    path_to_project = os.path.join(os.path.abspath('projects'), ctx.project_name)

    logging.debug('found project [{}]'.format(path_to_project))

    ec = 0
    containers = list()

    try:
        # TODO: project_name parameter causes image explosion - can this be avoided?
        #p = compose.cli.command.get_project(path_to_project, project_name=ctx.job_name)
        # Get the context for the Compose file
        p = compose.cli.command.get_project(path_to_project)

        # Bring up the services
        logging.debug('bringing up project [{}]'.format(p.name))
        containers = p.up()

        # Ensure that iRODS setup has completed on every machine in the topology
        logging.info('waiting for iRODS to finish setting up')
        for c in containers:
            if context.is_catalog_database_container(c): continue

            container = docker_client.containers.get(c.name)
            wait_for_setup_to_finish(container, args.setup_timeout)

        # Install the custom packages on all the iRODS containers, if specified.
        if args.package_directory:
            logging.warning('Installing packages from directory [{}]'.format(args.package_directory))
            install.install_irods_packages(docker_client, ctx.platform_name, ctx.database_name, args.package_directory, containers)

        configure_irods_testing(docker_client, containers)

        # Get the container on which the command is to be executed
        container = docker_client.containers.get(context.container_name(p.name, args.run_on))
        logging.debug('got container to run on [{}]'.format(container.name))

        # Serially execute the list of commands provided in the input
        for command in list(args.commands):
            # TODO: on --continue, save only failure ec's/commands
            ec = execute.execute_command(container, command, user='irods', workdir='/var/lib/irods', stream_output=True)

    except Exception as e:
        logging.critical(e)

        raise

    finally:
        logging.warning('collecting logs [{}]'.format(ctx.output_directory))
        logs.collect_logs(docker_client, containers, ctx.output_directory)

        p.down(include_volumes = True, remove_image_type = False)

    exit(ec)
