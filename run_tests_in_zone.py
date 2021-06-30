import docker

FLAG_FILE = '/var/lib/irods/setup_complete'

def wait_for_setup_to_finish(dc, c, timeout_in_seconds=0):
    import time

    start_time = time.time()

    while time.time() - start_time < timeout_in_seconds:
        exec_result = c.exec_run('stat {}'.format(FLAG_FILE))

        if exec_result[0] == 0:
            print('iRODS has been set up - continuing execution')
            break

        time.sleep(1)

def execute_on_project(project_name, container_name, command, dc):
    import compose.cli.command

    try:
        # Get the context for the Compose file
        p = compose.cli.command.get_project(project_name)

        # Bring up the services
        containers = p.up()

        # Get the container on which the command is to be executed
        c = dc.containers.get(container_name)

        # Ensure that iRODS setup has completed
        wait_for_setup_to_finish(dc, c, 10)

        # iRODS tests are meant to be run as the irods service account in the /var/lib/irods directory
        output_stream = c.exec_run(command, user='irods', workdir='/var/lib/irods', stream=True)

        try:
            # Stream output from the executing command
            while True: print(next(output_stream.output))

        except StopIteration:
            print('reached end of stream')

    except Exception as e:
        print(e)

        p.down(include_volumes = True, remove_image_type = False)

        raise

    else:
        print('we did it')

    finally:
        return p.down(include_volumes = True, remove_image_type = False)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Run iRODS tests in a consistent environment.')
    parser.add_argument('command', metavar='COMMAND', type=str,
                        help='The string representing the command to be run in the container')
    parser.add_argument('--container', metavar='CONTAINER', type=str,
                        default='irods_test_base_irods-catalog-provider_1',
                        help='The name of the container on which the command will run')
    #parser.add_argument('--platform', metavar='PLATFORM', type=str,
                        #help='The tag of the base Docker image to use (e.g. centos:7)')
    #parser.add_argument('--database', metavar='DATABASE', type=str,
                        #help='The tag of the database container to use (e.g. postgres:10.12')

    args = parser.parse_args()

    # TODO: modify project name based on selected platform and DB
    project_name = 'irods_test_base'

    exit(execute_on_project(project_name, args.container, args.command, docker.from_env()))
