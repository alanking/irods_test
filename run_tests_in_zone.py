import compose.cli.command
import docker

class execution_context:
    OUTPUT_ENCODING = 'utf-8'

    def __init__(self, project_name, args, dc):
        self.project_name   = project_name
        self.container_name = args.container
        self.commands       = list(args.commands)
        self.setup_timeout  = args.setup_timeout
        self.docker_client  = dc
        self.database       = args.database
        self.platform       = args.platform
        self.custom_packages = args.custom_packages

        if args.job_name:
            self.job_name = args.job_name
        else:
            import uuid
            self.job_name = str(uuid.uuid4())

        if args.log_output_directory:
            self.log_output_directory = args.log_output_directory
        else:
            import tempfile
            self.log_output_directory = tempfile.mkdtemp(prefix=self.project_name)

    def database_type(self):
        return self.database(':')[0]

def is_catalog_database_container(container):
    return 'icat' in container.name

def is_catalog_service_provider_container(container):
    return 'provider' in container.name

def execute_command(container, command, user='', workdir=None, verbose=True):
    exec_out = container.exec_run(command, user=user, workdir=workdir, stream=verbose)

    try:
        # Stream output from the executing command
        while verbose:
            print(next(exec_out.output).decode(execution_context.OUTPUT_ENCODING), end='')

    except StopIteration:
        print('\ndone')

    return exec_out.exit_code

def wait_for_setup_to_finish(dc, c, timeout_in_seconds):
    import time

    FLAG_FILE = '/var/lib/irods/setup_complete'

    print('waiting for iRODS to finish setting up [{}]'.format(c.name))

    start_time = time.time()
    now = start_time

    while now - start_time < timeout_in_seconds:
        if execute_command(c, 'stat {}'.format(FLAG_FILE), verbose=False) == 0:
            print('iRODS has been set up (waited [{}] seconds)'.format(str(now - start_time)))
            return

        time.sleep(1)
        now = time.time()

    raise SetupTimeoutError('timed out while waiting for iRODS to finish setting up')

def collect_logs(ctx, containers):
    import os.path

    LOGFILES_PATH = '/var/lib/irods/log'

    od = os.path.join(ctx.log_output_directory, ctx.project_name, ctx.platform, ctx.database, ctx.job_name)
    if not os.path.exists(od):
        os.makedirs(od)

    for c in containers:
        log_archive_path = os.path.join(od, c.name)

        print('saving log [{}]'.format(log_archive_path))

        try:
            # TODO: get server version to determine path of the log files
            bits, stat = ctx.docker_client.containers.get(c.name).get_archive(LOGFILES_PATH)
            print('stat [{0}] [{1}]'.format(LOGFILES_PATH, stat))

            with open(log_archive_path, 'wb') as f:
                for chunk in bits:
                    f.write(chunk)

        except Exception as e:
            print('failed to collect log [{}]'.format(log_archive_path))
            print(e)

def put_packages_in_container(container, tarfile_path):
    # Copy packages tarball into container
    path_to_tarfile_in_container = '/' + os.path.basename(tarfile_path)
    path_to_packages_dir_in_container = path_to_tarfile_in_container[:-4]

    with tarfile.open(tarfile_path, 'r') as tf:
        data = tf.read()
        if not c.put_archive(path_to_tarfile_in_container, data):
            raise RuntimeError('failed to put packages archive into container [{}]'.format(c.name))

        # untar into directory in /
        tf.extractall(path=path_to_packages_dir_in_container)

    return path_to_packages_dir_in_container

def install_package(p):
    return 'dpkg -i {}'.format(p)

def install_custom_packages(ctx, custom_packages_path):
    import glob
    import tarfile

    packages = list()
    for p in ['irods-runtime', 'irods-icommands', 'irods-server']:
        packages.append(glob.glob(os.path.join(custom_packages_path, p + '*.{}'.format(package_suffix)))[0])

    # Create a tarfile with the packages
    tarfile_name = ctx.job_name + '_packages.tar'
    tarfile_path = os.path.join(custom_packages_path, tarfile_name)

    # TODO: figure this out
    #import .irods_python_ci_utilities.get_package_suffix
    #package_suffix = irods_python_ci_utilities.get_package_suffix()
    package_suffix = '.deb'

    with tarfile.open(tarfile_path, 'w') as f:
        for p in packages:
            f.add(glob.glob(os.path.join(custom_packages_path, p + '*.{0}'.format(package_suffix)))[0])

    for c in ctx.containers:
        # Only the iRODS containers need to have packages installed
        if is_catalog_database_container(c): continue

        path_to_packages_in_container = put_packages_in_container(c, tarfile_path)

        # Install packages
        for p in packages:
            if execute_command(c, install_package(p)) != 0:
                raise RuntimeError('failed to install packages [{}]'.format(c.name))

        if is_catalog_service_provider_container(c):
            # TODO: Using the database provided by the context isn't going to work here because it's a docker image tag
            database_plugin = 'irods-plugin-database-{0}*.{1}'.format(ctx.database_type(), package_suffix)

            if execute_command(c, install_package(glob.glob(os.path.join(custom_packages_path, database_plugin))[0])):
                raise RuntimeError('failed to install database plugin [{}]'.format(c.name))

def execute_on_project(ctx):
    ec = 0
    containers = list()

    try:
        # Get the context for the Compose file
        p = compose.cli.command.get_project(ctx.project_name)

        # Bring up the services
        containers = p.up()

        # Get the container on which the command is to be executed
        c = ctx.docker_client.containers.get(ctx.container_name)

        # Ensure that iRODS setup has completed
        wait_for_setup_to_finish(ctx.docker_client, c, ctx.setup_timeout)

        # TODO: install desired version here
        if ctx.custom_packages:
            install_custom_packages(ctx.docker_client, ctx.custom_packages, containers)

        # Serially execute the list of commands provided in the input
        for command in ctx.commands:
            ec = execute_command(c, command, user='irods', workdir='/var/lib/irods')

    except Exception as e:
        print(e)

        p.down(include_volumes = True, remove_image_type = False)

        raise

    #else:
        #print('we did it')

    finally:
        print('collecting logs [{}]'.format(ctx.log_output_directory))
        collect_logs(ctx, containers)

        p.down(include_volumes = True, remove_image_type = False)

    return ec

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Run iRODS tests in a consistent environment.')
    parser.add_argument('commands', metavar='COMMANDS', nargs='+',
                        help='Space-delimited list of commands to be run')
    parser.add_argument('--run_on', metavar='CONTAINER', type=str, default='irods_test_base_irods-catalog-provider_1',
                        help='The name of the container on which the command will run')
    parser.add_argument('--setup_timeout', metavar='SETUP_TIMEOUT_IN_SECONDS', type=int, default=30,
                        help='How many seconds to wait before timing out while waiting on iRODS server to be set up.')
    parser.add_argument('--log_output_directory', metavar='FULLPATH_TO_DIRECTORY_FOR_OUTPUT_LOGS', type=str,
                        help='Full path to local directory for output logs which will be copied from the containers.')
    parser.add_argument('--platform', metavar='PLATFORM', type=str, default='ubuntu:18.04',
                        help='The tag of the base Docker image to use (e.g. centos:7)')
    parser.add_argument('--database', metavar='DATABASE', type=str, default='postgres:10.12',
                        help='The tag of the database container to use (e.g. postgres:10.12')
    parser.add_argument('--job_name', metavar='JOB_NAME', type=str,
                        help='Name of the test run')
    parser.add_argument('--custom_packages', metavar='FULLPATH_TO_DIRECTORY_WITH_PACKAGES', type=str,
                        help='Full path to local directory which contains packages to be installed on iRODS containers.')

    args = parser.parse_args()

    # TODO: modify project name based on selected platform and DB
    project_name = 'irods_test_base'

    exit(execute_on_project(execution_context(project_name, args, docker.from_env())))
