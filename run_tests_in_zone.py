import compose.cli.command
import docker
import os
import logging

import execute

# TODO: Way to know the absolute path of the thing that is actually running (this script)
#script_path = os.path.dirname(os.path.realpath(__file__))

def init_logger(verbosity=1, log_filename=None):
    # CRITICAL messages will always be printed, but anything after that is a function of the number of -v
    level = logging.CRITICAL - 10 * verbosity

    handlers = [logging.StreamHandler()]

    if log_filename:
        handlers.append(logging.FileHandler(os.path.abspath(log_filename)))

    logging.basicConfig(
        level = level if level > logging.NOTSET else logging.DEBUG,
        format = '%(asctime)-15s %(levelname)s - %(message)s',
        handlers = handlers
    )

class execution_context:
    package_context = {
        'centos' : {
            'command' : 'rpm -U --force',
            'extension' : 'rpm'
         },
        'ubuntu' : {
            'command' : 'dpkg -i',
            'extension' : 'deb'
        }
    }

    PROJECT_NAME = 'irods_test_base'

    def __init__(self, args, dc):
        self.docker_client  = dc
        self.run_on         = args.run_on
        self.commands       = list(args.commands)
        self.setup_timeout  = args.setup_timeout
        self.custom_packages = args.custom_packages

        self.platform_name, self.platform_version = args.platform.split(':')
        self.database_name, self.database_version = args.database.split(':')

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

def is_catalog_database_container(container):
    return 'icat' in container.name

def is_catalog_service_provider_container(container):
    return 'provider' in container.name

def is_database_plugin(p):
    return 'database' in p

def wait_for_setup_to_finish(c, timeout_in_seconds):
    import time

    FLAG_FILE = '/var/lib/irods/setup_complete'

    logging.warning('waiting for iRODS to finish setting up [{}]'.format(c.name))

    start_time = time.time()
    now = start_time

    while now - start_time < timeout_in_seconds:
        if execute.execute_command(c, 'stat {}'.format(FLAG_FILE)) == 0:
            logging.warning('iRODS has been set up (waited [{}] seconds)'.format(str(now - start_time)))
            return

        time.sleep(1)
        now = time.time()

    raise RuntimeError('timed out while waiting for iRODS to finish setting up')

def collect_logs(docker_client, containers, output_directory, logfile_path='/var/lib/irods/log'):
    od = os.path.join(output_directory, 'logs')
    if not os.path.exists(od):
        os.makedirs(od)

    for c in containers:
        if is_catalog_database_container(c): continue

        log_archive_path = os.path.join(od, c.name)

        logging.info('saving log [{}]'.format(log_archive_path))

        try:
            # TODO: get server version to determine path of the log files
            bits, _ = docker_client.containers.get(c.name).get_archive(logfile_path)

            with open(log_archive_path, 'wb') as f:
                for chunk in bits:
                    f.write(chunk)

        except Exception as e:
            logging.error('failed to collect log [{}]'.format(log_archive_path))
            logging.error(e)

def put_packages_in_container(container, tarfile_path):
    # Copy packages tarball into container
    path_to_packages_dir_in_container = '/' + os.path.basename(tarfile_path)[:len('.tar') * -1]

    logging.info('putting tarfile [{0}] in container [{1}] at [{2}]'.format(
        tarfile_path, container.name, path_to_packages_dir_in_container))

    with open(tarfile_path, 'rb') as tf:
        if not container.put_archive('/', tf):
            raise RuntimeError('failed to put packages archive into container [{}]'.format(container.name))

    return path_to_packages_dir_in_container


def install_package(container, platform, full_path_to_package):
    cmd = ' '.join([execution_context.package_context[platform.lower()]['command'], full_path_to_package])

    execute.execute_command(container, cmd)

def create_tarfile(ctx, members):
    import tarfile

    # Create a tarfile with the packages
    tarfile_name = ctx.job_name + '_packages.tar'
    tarfile_path = os.path.join(ctx.output_directory, tarfile_name)

    logging.info('creating tarfile [{}]'.format(tarfile_path))

    with tarfile.open(tarfile_path, 'w') as f:
        for m in members:
            logging.debug('adding member [{0}] to tarfile'.format(m))
            f.add(m)

    return tarfile_path

def get_package_list(ctx):
    import glob

    if not ctx.custom_packages:
        raise RuntimeError('Attempting to install custom packages from unspecified location')

    package_suffix = execution_context.package_context[ctx.platform_name.lower()]['extension']

    package_path = os.path.abspath(ctx.custom_packages)

    logging.debug('listing for [{}]:\n{}'.format(package_path, os.listdir(package_path)))

    packages = list()

    for p in ['irods-runtime', 'irods-icommands', 'irods-server', 'irods-database-plugin-{}'.format(ctx.database_name)]:
        p_glob = os.path.join(package_path, p + '*.{}'.format(package_suffix))

        logging.debug('looking for packages like [{}]'.format(p_glob))

        packages.append(glob.glob(p_glob)[0])

    return packages

def irodsctl(container, cmd):
    execute.execute_command(container, '/var/lib/irods/irodsctl ' + cmd, user='irods')

def install_custom_packages(ctx, containers):
    package_suffix = execution_context.package_context[ctx.platform_name.lower()]['extension']

    packages = get_package_list(ctx)

    logging.info('packages to install [{}]'.format(packages))

    tarfile_path = create_tarfile(ctx, packages)

    for c in containers:
        # Only the iRODS containers need to have packages installed
        if is_catalog_database_container(c): continue

        container = ctx.docker_client.containers.get(c.name)

        irodsctl(container, 'stop')

        path_to_packages_in_container = put_packages_in_container(container, tarfile_path)

        package_list = ' '.join([p for p in packages if not is_database_plugin(p) or is_catalog_service_provider_container(container)])

        cmd = ' '.join([execution_context.package_context[ctx.platform_name.lower()]['command'], package_list])

        execute.execute_command(container, cmd)

        irodsctl(container, 'restart')

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST or not os.path.isdir(path):
            raise

if __name__ == "__main__":
    import argparse

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
    parser.add_argument('--install-packages-from', '-i', metavar='PATH_TO_DIRECTORY_WITH_PACKAGES', dest='custom_packages', type=str,
                        help='Full path to local directory which contains packages to be installed on iRODS containers.')
    parser.add_argument('--verbose', '-v', dest='verbosity', action='count', default=1,
                        help='Increase the level of output to stdout. CRITICAL and ERROR messages will always be printed.')

    args = parser.parse_args()

    ctx = execution_context(args, docker.from_env())

    mkdir_p(ctx.output_directory)

    init_logger(args.verbosity, os.path.join(ctx.output_directory, 'script_output.log'))

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

        # Get the container on which the command is to be executed
        c = ctx.docker_client.containers.get('_'.join([p.name, ctx.run_on, '1']))
        logging.debug('got container to run on [{}]'.format(c.name))

        # Ensure that iRODS setup has completed
        wait_for_setup_to_finish(c, ctx.setup_timeout)

        # Install the custom packages on all the iRODS containers, if specified.
        if ctx.custom_packages:
            install_custom_packages(ctx, containers)

        # Serially execute the list of commands provided in the input
        for command in ctx.commands:
            # TODO: on --continue, save only failure ec's/commands
            ec = execute.execute_command(c, command, user='irods', workdir='/var/lib/irods', stream_output=True)

    except Exception as e:
        logging.critical(e)

        raise

    finally:
        logging.info('collecting logs [{}]'.format(ctx.output_directory))
        collect_logs(ctx.docker_client, containers, ctx.output_directory)

        p.down(include_volumes = True, remove_image_type = False)

    exit(ec)
