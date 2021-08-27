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
    import concurrent.futures
    import logs

    parser = argparse.ArgumentParser(description='Install a list of packages on a docker-compose project.')
    parser.add_argument('project_path', metavar='PROJECT_PATH', type=str,
                        help='Path to the docker-compose project on which packages will be installed.')
    parser.add_argument('--project-name', metavar='PROJECT_NAME', type=str, dest='project_name',
                        help='Name of the docker-compose project on which to install packages.')
    parser.add_argument('--database-tag', '-d', metavar='DATABASE_IMAGE_TAG', dest='database', type=str, default='postgres:10.12',
                        help='The tag of the database container to use (e.g. postgres:10.12')
    parser.add_argument('--exclude-catalog-setup', dest='setup_catalog', action='store_false',
                        help='If indicated, skips the setup of iRODS tables and postgres user in the database.')
    parser.add_argument('--exclude-irods-catalog-provider-setup', dest='setup_irods_catalog_provider', action='store_false',
                        help='If indicated, skips running the iRODS setup script on the catalog service provider.')
    parser.add_argument('--irods-catalog-consumer-count', '-n', dest='irods_catalog_consumer_count', type=int, default=1,
                        help='Indicates how many catalog service consumer instances must be set up.')
    parser.add_argument('--verbose', '-v', dest='verbosity', action='count', default=1,
                        help='Increase the level of output to stdout. CRITICAL and ERROR messages will always be printed.')

    args = parser.parse_args()

    logs.configure(args.verbosity)

    if args.irods_catalog_consumer_count < 1:
        print('invalid input for --irods-catalog-consumer-count [{}]'.format(args.irods_catalog_consumer_count))
        exit(1)

    docker_client = docker.from_env()

    p = compose.cli.command.get_project(os.path.abspath(args.project_path), project_name=args.project_name)

    try:
        if args.setup_catalog:
            database_setup.setup_catalog(docker_client, p.name, args.database)

        if args.setup_irods_catalog_provider:
            irods_setup.setup_irods_catalog_provider(docker_client, p.name)

        rc = 0
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # range() is 0-based, so add 1 to match the service instance numbering scheme of docker-compose
            futures_to_containers = {executor.submit(irods_setup.setup_irods_catalog_consumer, docker_client, p.name, 1, (i + 1)): i for i in range(args.irods_catalog_consumer_count)}
            logging.debug(futures_to_containers)

            for f in concurrent.futures.as_completed(futures_to_containers):
                instance = futures_to_containers[f]
                container_name = context.irods_catalog_consumer_container(p.name, instance + 1)
                try:
                    f.result()
                    logging.info('setup completed successfully [{}]'.format(container_name))

                except Exception as e:
                    logging.error('exception raised while setting up iRODS [{}]'.format(container_name))
                    logging.error(e)
                    rc = 1

        exit(rc)

    except Exception as e:
        logging.critical(e)
        raise

