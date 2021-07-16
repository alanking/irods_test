import compose.cli.command
import docker
import os

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

    OUTPUT_ENCODING = 'utf-8'
    PROJECT_NAME = 'irods_test_base'

    def __init__(self, args, dc):
        self.run_on         = args.run_on
        self.commands       = list(args.commands)
        self.setup_timeout  = args.setup_timeout
        self.docker_client  = dc
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
            self.job_name = '_'.join([str(uuid.uuid4()), self.project_name])

        if args.output_directory:
            self.output_directory = args.output_directory
        else:
            import tempfile
            self.output_directory = tempfile.mkdtemp(prefix=self.project_name)

    def database_type(self):
        return self.database(':')[0]

def is_catalog_database_container(container):
    return 'icat' in container.name

def is_catalog_service_provider_container(container):
    return 'provider' in container.name

def is_database_plugin(p):
    return 'database' in p

def execute_command(container, command, user='', workdir=None, verbose=True):
    if verbose:
        print('executing on [{0}] [{1}]'.format(container.name, command))

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

    raise RuntimeError('timed out while waiting for iRODS to finish setting up')

def collect_logs(ctx, containers):
    LOGFILES_PATH = '/var/lib/irods/log'

    od = os.path.join(ctx.output_directory, ctx.job_name, 'logs')
    if not os.path.exists(od):
        os.makedirs(od)

    for c in containers:
        if is_catalog_database_container(c): continue

        log_archive_path = os.path.join(od, c.name)

        print('saving log [{}]'.format(log_archive_path))

        try:
            # TODO: get server version to determine path of the log files
            bits, _ = ctx.docker_client.containers.get(c.name).get_archive(LOGFILES_PATH)

            with open(log_archive_path, 'wb') as f:
                for chunk in bits:
                    f.write(chunk)

        except Exception as e:
            print('failed to collect log [{}]'.format(log_archive_path))
            print(e)

def put_packages_in_container(container, tarfile_path):
    # Copy packages tarball into container
    path_to_packages_dir_in_container = '/' + os.path.basename(tarfile_path)[:len('.tar') * -1]

    print('putting tarfile [{0}] in container [{1}] at [{2}]'.format(
        tarfile_path, container.name, path_to_packages_dir_in_container))

    with open(tarfile_path, 'rb') as tf:
        if not container.put_archive('/', tf):
            raise RuntimeError('failed to put packages archive into container [{}]'.format(container.name))

    return path_to_packages_dir_in_container


def install_package(container, platform, full_path_to_package):
    cmd = ' '.join([execution_context.package_context[platform.lower()]['command'], full_path_to_package])

    #ec = execute_command(container, cmd)

    #if ec != 0:
        #raise RuntimeError('failed to install package [{0}] on [{1}] [ec=[{2}]]'.format(p, container.name, ec))

    #return ec

    execute_command(container, cmd)

def create_tarfile(ctx, members):
    import tarfile

    # Create a tarfile with the packages
    tarfile_name = ctx.job_name + '_packages.tar'
    tarfile_path = os.path.join(ctx.output_directory, tarfile_name)

    print('creating tarfile [{}]'.format(tarfile_path))

    with tarfile.open(tarfile_path, 'w') as f:
        for m in members:
            print('adding member [{0}] to tarfile'.format(m))
            f.add(m)

    return tarfile_path

def get_package_list(ctx):
    import glob

    package_suffix = execution_context.package_context[ctx.platform_name.lower()]['extension']

    print('listing for [{}]:\n{}'.format(ctx.custom_packages, os.listdir(ctx.custom_packages)))

    packages = list()

    for p in ['irods-runtime', 'irods-icommands', 'irods-server']:
        p_glob = os.path.join(ctx.custom_packages, p + '*.{}'.format(package_suffix))

        print('looking for packages like [{}]'.format(p_glob))

        packages.append(glob.glob(p_glob)[0])

    # TODO: maybe care about which DB plugins we are installing
    for p in glob.glob(os.path.join(ctx.custom_packages, 'irods-database-plugin-*.{}'.format(package_suffix))):
        packages.append(p)

    return packages

def restart_irods(c):
    #if execute_command(c, '/var/lib/irods/irodsctl restart', user='irods') != 0:
        #raise RuntimeError('Failed to restart iRODS server [{}]'.format(c.name))
    execute_command(c, '/var/lib/irods/irodsctl restart', user='irods')

def install_custom_packages(ctx, containers):
    # TODO: figure this out
    #import .irods_python_ci_utilities.get_package_suffix
    #package_suffix = irods_python_ci_utilities.get_package_suffix()
    package_suffix = execution_context.package_context[ctx.platform_name.lower()]['extension']

    packages = get_package_list(ctx)

    print('packages to install [{}]'.format(packages))

    tarfile_path = create_tarfile(ctx, packages)

    for c in containers:
        # Only the iRODS containers need to have packages installed
        if is_catalog_database_container(c): continue

        container = ctx.docker_client.containers.get(c.name)

        path_to_packages_in_container = put_packages_in_container(container, tarfile_path)

        for p in packages:
            if is_database_plugin(p) and not is_catalog_service_provider_container(c): continue

            install_package(container, ctx.platform_name, p)

        restart_irods(container)

def execute_on_project(ctx):
    ec = 0
    containers = list()

    try:
        # Get the context for the Compose file
        p = compose.cli.command.get_project(ctx.project_name)

        # Bring up the services
        containers = p.up()

        # Get the container on which the command is to be executed
        c = ctx.docker_client.containers.get(ctx.run_on)

        # Ensure that iRODS setup has completed
        wait_for_setup_to_finish(ctx.docker_client, c, ctx.setup_timeout)

        # Install the custom packages on all the iRODS containers, if specified.
        if ctx.custom_packages:
            install_custom_packages(ctx, containers)

        # Serially execute the list of commands provided in the input
        for command in ctx.commands:
            # TODO: on --continue, save only failure ec's/commands
            ec = execute_command(c, command, user='irods', workdir='/var/lib/irods')

    except Exception as e:
        print(e)

        raise

    finally:
        print('collecting logs [{}]'.format(ctx.output_directory))
        collect_logs(ctx, containers)

        p.down(include_volumes = True, remove_image_type = False)

    return ec

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Run iRODS tests in a consistent environment.')
    parser.add_argument('commands', metavar='COMMANDS', nargs='+',
                        help='Space-delimited list of commands to be run')
    parser.add_argument('--run_on', metavar='CONTAINER', type=str, default='irods-catalog-provider',
                        help='The name of the container on which the command will run')
    parser.add_argument('--setup_timeout', metavar='SETUP_TIMEOUT_IN_SECONDS', type=int, default=30,
                        help='How many seconds to wait before timing out while waiting on iRODS server to be set up.')
    parser.add_argument('--output_directory', metavar='FULLPATH_TO_DIRECTORY_FOR_OUTPUT', type=str,
                        help='Full path to local directory for output from execution.')
    parser.add_argument('--platform', metavar='PLATFORM', type=str, default='ubuntu:18.04',
                        help='The tag of the base Docker image to use (e.g. centos:7)')
    parser.add_argument('--database', metavar='DATABASE', type=str, default='postgres:10.12',
                        help='The tag of the database container to use (e.g. postgres:10.12')
    parser.add_argument('--job_name', metavar='JOB_NAME', type=str,
                        help='Name of the test run')
    parser.add_argument('--custom_packages', metavar='FULLPATH_TO_DIRECTORY_WITH_PACKAGES', type=str,
                        help='Full path to local directory which contains packages to be installed on iRODS containers.')

    args = parser.parse_args()

    ctx = execution_context(args, docker.from_env())

    path_to_project = os.path.join(os.path.abspath('projects'), ctx.project_name)

    print(path_to_project)

    #exit(execute_on_project(ctx))

    ec = 0
    containers = list()

    try:
        # Get the context for the Compose file
        p = compose.cli.command.get_project(path_to_project, project_name=ctx.job_name)

        # Bring up the services
        containers = p.up()

        # Get the container on which the command is to be executed
        c = ctx.docker_client.containers.get('_'.join([p.name, args.run_on, '1']))

        # Ensure that iRODS setup has completed
        wait_for_setup_to_finish(ctx.docker_client, c, ctx.setup_timeout)

        # Install the custom packages on all the iRODS containers, if specified.
        if ctx.custom_packages:
            install_custom_packages(ctx, containers)

        # Serially execute the list of commands provided in the input
        for command in ctx.commands:
            # TODO: on --continue, save only failure ec's/commands
            ec = execute_command(c, command, user='irods', workdir='/var/lib/irods')

    except Exception as e:
        print(e)

        raise

    finally:
        print('collecting logs [{}]'.format(ctx.output_directory))
        collect_logs(ctx, containers)

        p.down(include_volumes = True, remove_image_type = False)

    exit(ec)
