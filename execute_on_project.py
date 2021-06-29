import compose.cli.command
import docker
import os, time

FLAG_FILE = '/var/lib/irods/setup_complete'

def get_project(name):
    return compose.cli.command.get_project(name)

def wait_for_setup_to_finish(dc, c, timeout_in_seconds=0):
    start_time = time.time()

    while time.time() - start_time < timeout_in_seconds:
        exec_result = c.exec_run('stat {}'.format(FLAG_FILE))
        print(exec_result[1])
        if exec_result[0] == 0:
            break

        time.sleep(1)

def execute_on_project(project_name, container_name, command, dc=docker.from_env()):
    try:
        # Get the context for the Compose file
        p = get_project(project_name)

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

if __name__ == '__main__':
    exit(execute_on_project('irods_test_base', 'irods_test_base_irods-catalog-consumer-resource1_1', 'echo "hello"'))
