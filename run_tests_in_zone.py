import docker

FLAG_FILE = '/var/lib/irods/setup_complete'

class execution_context:
    def __init__(self, project_name, args, dc):
        self.project_name   = project_name
        self.container_name = args.container
        self.commands       = args.command
        self.setup_timeout  = args.setup_timeout
        self.docker_client  = dc

def wait_for_setup_to_finish(dc, c, timeout_in_seconds):
    import time

    print('waiting for iRODS to finish setting up [{}]'.format(c.name))

    start_time = time.time()

    while time.time() - start_time < timeout_in_seconds:
        exec_result = c.exec_run('stat {}'.format(FLAG_FILE))

        if exec_result[0] == 0:
            print('iRODS has been set up - continuing execution')
            return

        time.sleep(1)

    raise SetupTimeoutError('timed out while waiting for iRODS to finish setting up')

def execute_on_project(ctx):
    import compose.cli.command

    ec = 0

    try:
        # Get the context for the Compose file
        p = compose.cli.command.get_project(ctx.project_name)

        # Bring up the services
        containers = p.up()

        # Get the container on which the command is to be executed
        c = ctx.docker_client.containers.get(ctx.container_name)

        # Ensure that iRODS setup has completed
        wait_for_setup_to_finish(ctx.docker_client, c, ctx.setup_timeout)

        # iRODS tests are meant to be run as the irods service account in the /var/lib/irods directory
        # TODO: loop through commands and run them serially
        exec_out = c.exec_run(ctx.commands, user='irods', workdir='/var/lib/irods', stream=True)

        try:
            # Stream output from the executing command
            while True: print(str(next(exec_out.output)))

            ec = exec_out.exit_code

        except StopIteration:
            print('reached end of stream')

    except Exception as e:
        print(e)

        p.down(include_volumes = True, remove_image_type = False)

        raise

    #else:
        #print('we did it')

    finally:
        p.down(include_volumes = True, remove_image_type = False)

    return ec

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Run iRODS tests in a consistent environment.')
    parser.add_argument('command', metavar='COMMAND', type=str,
                        help='The string representing the command to be run in the container')
    parser.add_argument('--container', metavar='CONTAINER', type=str,
                        default='irods_test_base_irods-catalog-provider_1',
                        help='The name of the container on which the command will run')
    parser.add_argument('--setup_timeout', metavar='SETUP_TIMEOUT_IN_SECONDS', type=int, default=10,
                        help='How many seconds to wait before timing out while waiting on iRODS server to be set up.')
    #parser.add_argument('--platform', metavar='PLATFORM', type=str,
                        #help='The tag of the base Docker image to use (e.g. centos:7)')
    #parser.add_argument('--database', metavar='DATABASE', type=str,
                        #help='The tag of the database container to use (e.g. postgres:10.12')

    args = parser.parse_args()

    # TODO: modify project name based on selected platform and DB
    project_name = 'irods_test_base'

    exit(execute_on_project(execution_context(project_name, args, docker.from_env())))
