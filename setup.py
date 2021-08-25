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
                  instance_number='1',
                  database_name='ICAT',
                  database_user='irods',
                  database_password='testpassword'):

    container = '_'.join([project_name, catalog_service_name, instance_number])

    create_database = 'create database "{}"'.format(database_name)
    create_user = 'create user {0} with password {1}'.format(database_user, database_password)
    elevate_privileges = 'grant all privileges on database {0} to {1}'.format(database_name, database_user)

    for psql_cmd in [create_database, create_user, elevate_privileges, '\l']:
        cmd = 'psql -c "{}"'.format(psql_cmd)
        execute.execute_command(container, cmd, user='postgres')

if __name__ == "__main__":
    import argparse
    import logs

    parser = argparse.ArgumentParser(description='Install a list of packages on a docker-compose project.')
    parser.add_argument('project', metavar='PROJECT_NAME', type=str,
                        help='Name of the docker-compose project on which to install packages.')
    parser.add_argument('--os-platform-tag', '-p', metavar='OS_PLATFORM_IMAGE_TAG', dest='platform', type=str,
                        help='The tag of the base Docker image to use (e.g. centos:7)')
    parser.add_argument('--database-tag', '-d', metavar='DATABASE_IMAGE_TAG', dest='database', type=str, default='postgres:10.12',
                        help='The tag of the database container to use (e.g. postgres:10.12')
    parser.add_argument('--verbose', '-v', dest='verbosity', action='count', default=1,
                        help='Increase the level of output to stdout. CRITICAL and ERROR messages will always be printed.')

    args = parser.parse_args()

    logs.configure(args.verbosity)

    base_path_to_project = os.path.join(os.path.abspath('projects'), 'base')

    path_to_project = os.path.join(base_path_to_project, args.platform, args.database)

    p = compose.cli.command.get_project(path_to_project, project_name=args.project)

    try:
        ec = setup_catalog(docker_client, p.name)

        if ec is not 0:
            exit(ec)

    except Exception as e:
        logging.critical(e)

        raise

