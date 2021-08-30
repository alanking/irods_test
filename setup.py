# grown-up modules
import compose.cli.command
import docker
import logging
import os

# local modules
import context
import database_setup
import irods_setup

if __name__ == "__main__":
    import argparse
    import logs

    parser = argparse.ArgumentParser(description='Install a list of packages on a docker-compose project.')
    parser.add_argument('--project-directory', metavar='PATH_TO_PROJECT_DIRECTORY', type=str, dest='project_directory', default='.',
                        help='Path to the docker-compose project on which packages will be installed.')
    parser.add_argument('--project-name', metavar='PROJECT_NAME', type=str, dest='project_name',
                        help='Name of the docker-compose project on which to install packages.')
    parser.add_argument('--database-tag', '-d', metavar='DATABASE_IMAGE_TAG', dest='database', type=str,
                        help='The tag of the database image to use')
    parser.add_argument('--exclude-catalog-setup', dest='setup_catalog', action='store_false',
                        help='If indicated, skips the setup of iRODS tables and postgres user in the database.')
    parser.add_argument('--exclude-irods-catalog-provider-setup', dest='setup_irods_catalog_provider', action='store_false',
                        help='If indicated, skips running the iRODS setup script on the catalog service provider.')
    parser.add_argument('--verbose', '-v', dest='verbosity', action='count', default=1,
                        help='Increase the level of output to stdout. CRITICAL and ERROR messages will always be printed.')

    args = parser.parse_args()

    logs.configure(args.verbosity)

    docker_client = docker.from_env()

    p = compose.cli.command.get_project(os.path.abspath(args.project_directory), project_name=args.project_name)
    logging.debug('provided project name [{0}], docker-compose project name [{1}]'.format(args.project_name, p.name))

    if len(p.containers()) is 0:
        logging.critical(
            'no containers found for project [directory=[{0}], name=[{1}]]'.format(
            os.path.abspath(args.project_directory), args.project_name))

        exit(1)

    try:
        if args.setup_catalog:
            if args.database:
                database = args.database
                logging.debug('provided database image tag [{}]'.format(database))
            else:
                # divine the database image tag if it is not provided
                project_name = args.project_name if args.project_name else p.name
                database = context.database_image_tag(project_name)
                logging.debug('derived database image tag [{}]'.format(database))

            database_setup.setup_catalog(docker_client, p.name, database)

        if args.setup_irods_catalog_provider:
            irods_setup.setup_irods_catalog_provider(docker_client, p.name)

        irods_setup.setup_irods_catalog_consumers(docker_client, p)

    except Exception as e:
        logging.critical(e)
        raise

