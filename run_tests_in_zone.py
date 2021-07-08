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

def wait_for_setup_to_finish(dc, c, timeout_in_seconds):
    import time

    FLAG_FILE = '/var/lib/irods/setup_complete'

    print('waiting for iRODS to finish setting up [{}]'.format(c.name))

    start_time = time.time()
    now = start_time

    while now - start_time < timeout_in_seconds:
        exec_result = c.exec_run('stat {}'.format(FLAG_FILE))

        if exec_result.exit_code == 0:
            print('iRODS has been set up (waited [{}] seconds)'.format(str(now - start_time)))
            return

        time.sleep(1)
        now = time.time()

    raise SetupTimeoutError('timed out while waiting for iRODS to finish setting up')

def execute_command_with_output(container, command):
    ec = 0

    # iRODS tests are meant to be run as the irods service account in the /var/lib/irods directory
    exec_out = container.exec_run(command, user='irods', workdir='/var/lib/irods', stream=True)

    try:
        # Stream output from the executing command
        while True:
            print(next(exec_out.output).decode(execution_context.OUTPUT_ENCODING), end='')

        ec = exec_out.exit_code

    except StopIteration:
        print('\ndone')

    return ec

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

def install_custom_packages(docker_client, path_to_packages, containers):
    for c in containers:

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
            print('----\nexecuting command [{}]'.format(command))
            ec = execute_command_with_output(c, command)
            print('\nexecution complete\n----')

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
