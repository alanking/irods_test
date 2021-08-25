# grown-up modules
import compose.cli.command
import docker
import logging
import os

# local modules
import context
import execute

# TODO: Strategy for different databases
def setup_catalog(docker_client,
                  project_name,
                  catalog_service_name='catalog',
                  instance_number=1,
                  database_name='ICAT',
                  database_user='irods',
                  database_password='testpassword'):

    container_name = context.container_name(project_name, catalog_service_name, str(instance_number))
    container = docker_client.containers.get(container_name)

    create_database = 'create database \\\"{}\\\";'.format(database_name)
    create_user = 'create user {0} with password \'{1}\';'.format(database_user, database_password)
    elevate_privileges = 'grant all privileges on database \\\"{0}\\\" to {1};'.format(database_name, database_user)

    for psql_cmd in [create_database, create_user, elevate_privileges, '\l']:
        cmd = 'psql -c \"{}\"'.format(psql_cmd)
        execute.execute_command(container, cmd, user='postgres')

if __name__ == "__main__":
    import argparse
    import logs

    parser = argparse.ArgumentParser(description='Install a list of packages on a docker-compose project.')
    parser.add_argument('project_path', metavar='PROJECT_PATH', type=str,
                        help='Path to the docker-compose project on which packages will be installed.')
    parser.add_argument('--project-name', metavar='PROJECT_NAME', type=str, dest='project_name',
                        help='Name of the docker-compose project on which to install packages.')
    parser.add_argument('--verbose', '-v', dest='verbosity', action='count', default=1,
                        help='Increase the level of output to stdout. CRITICAL and ERROR messages will always be printed.')

    args = parser.parse_args()

    logs.configure(args.verbosity)

    docker_client = docker.from_env()

    p = compose.cli.command.get_project(os.path.abspath(args.project_path), project_name=args.project_name)

    try:
        ec = setup_catalog(docker_client, p.name)

        if ec is not 0:
            exit(ec)

    except Exception as e:
        logging.critical(e)

        raise

