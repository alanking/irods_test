import compose.cli.command
import docker
import os

from . import execution_context

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
            execution_context.install_custom_packages(ctx, containers)

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

    ctx = execution_context.execution_context(args, docker.from_env())

    path_to_project = os.path.join(os.path.abspath('projects'), ctx.project_name)

    print(path_to_project)

    #exit(execute_on_project(ctx))

    ec = 0
    containers = list()

    try:
        # TODO: project_name parameter causes image explosion - can this be avoided?
        #p = compose.cli.command.get_project(path_to_project, project_name=ctx.job_name)
        # Get the context for the Compose file
        p = compose.cli.command.get_project(path_to_project)

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
