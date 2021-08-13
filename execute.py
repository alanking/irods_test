import docker
import logging
import os

def execute_command(container, command, user='', workdir=None, stream_output=False):
    OUTPUT_ENCODING = 'utf-8'

    logging.debug('executing on [{0}] [{1}]'.format(container.name, command))

    exec_instance = container.client.api.exec_create(container.id, command, user=user, workdir=workdir)
    exec_out = container.client.api.exec_start(exec_instance['Id'], stream=stream_output)

    previous_log_level = logging.getLogger().getEffectiveLevel()
    if previous_log_level > logging.INFO:
        logging.getLogger().setLevel(logging.INFO)

    try:
        # Stream output from the executing command. A StopIteration exception is raised
        # by the generator returned by the docker-py API when there is no more output.
        while stream_output:
            logging.info(next(exec_out).decode(OUTPUT_ENCODING))

    except StopIteration:
        logging.debug('done')

    finally:
        logging.getLogger().setLevel(previous_log_level)

    if not stream_output:
        logging.debug(exec_out.decode(OUTPUT_ENCODING))

    return container.client.api.exec_inspect(exec_instance['Id'])['ExitCode']

if __name__ == "__main__":
    import argparse
    import logs

    parser = argparse.ArgumentParser(description='Run commands on a running container as iRODS service account.')
    parser.add_argument('commands', metavar='COMMANDS', nargs='+',
                        help='Space-delimited list of commands to be run')
    parser.add_argument('--run-on-container', '-t', metavar='TARGET_CONTAINER', dest='run_on', type=str,
                        help='The name of the container on which the command will run')
    parser.add_argument('--verbose', '-v', dest='verbosity', action='count', default=1,
                        help='Increase the level of output to stdout. CRITICAL and ERROR messages will always be printed.')

    args = parser.parse_args()

    logs.configure(args.verbosity)

    ec = 0
    containers = list()

    dc = docker.from_env()

    try:
        # TODO: project_name parameter causes image explosion - can this be avoided?
        #p = compose.cli.command.get_project(path_to_project, project_name=ctx.job_name)

        # Get the container on which the command is to be executed
        c = dc.containers.get(args.run_on)
        logging.debug('got container to run on [{}]'.format(c.name))

        # Serially execute the list of commands provided in the input
        for command in args.commands:
            # TODO: on --continue, save only failure ec's/commands
            ec = execute_command(c, command, user='irods', workdir='/var/lib/irods', stream_output=True)

    except Exception as e:
        logging.critical(e)

        raise

    exit(ec)
