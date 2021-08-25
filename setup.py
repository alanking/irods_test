# grown-up modules
import compose.cli.command
import docker
import logging
import os

# local modules
import context
import execute

class database_setup_strategy(object):
    def __init__(self, container):
        self.container = container

    def execute_psql_command(self, psql_cmd):
        raise NotImplementedError('method not implemented for database strategy')

    def create_database(self, name):
        raise NotImplementedError('method not implemented for database strategy')

    def create_user(self, username, password):
        raise NotImplementedError('method not implemented for database strategy')

    def grant_privileges(self, database, username):
        raise NotImplementedError('method not implemented for database strategy')

    def drop_database(self, name):
        raise NotImplementedError('method not implemented for database strategy')

    def drop_user(self, username):
        raise NotImplementedError('method not implemented for database strategy')

class postgres_database_setup_strategy(database_setup_strategy):
    def __init__(self, container):
        super().__init__(container)

    def execute_psql_command(self, psql_cmd):
        cmd = 'psql -c \"{}\"'.format(psql_cmd)
        return execute.execute_command(self.container, cmd, user='postgres')

    def create_database(self, name):
        return self.execute_psql_command(
            'create database \\\"{}\\\";'.format(name))

    def create_user(self, username, password):
        return self.execute_psql_command(
            'create user {0} with password \'{1}\';'.format(username, password))

    def grant_privileges(self, database, username):
        return self.execute_psql_command(
            'grant all privileges on database \\\"{0}\\\" to {1};'.format(database, username))

    def drop_database(self, name):
        return self.execute_psql_command(
            'drop database \\\"{}\\\";'.format(name))

    def drop_user(self, username):
        return self.execute_psql_command(
            'drop user {};'.format(username))

    def list_databases(self):
        return self.execute_psql_command('\l')

def make_database_setup_strategy(database, container):
    suffix = '_database_setup_strategy'
    return eval(context.image_name(database) + suffix)(container)

def setup_catalog(docker_client,
                  project_name,
                  database_tag,
                  service_instance=1,
                  database_name='ICAT',
                  database_user='irods',
                  database_password='testpassword'):

    container_name = context.irods_catalog_database_container(project_name, service_instance)

    container = docker_client.containers.get(container_name)

    strat = make_database_setup_strategy(database_tag, container)

    ec = strat.create_database(database_name)
    if ec is not 0:
        return ec

    ec = strat.create_user(database_user, database_password)
    if ec is not 0:
        #strat.drop_database(database_name)
        return ec

    ec = strat.grant_privileges(database_name, database_user)
    if ec is not 0:
        #strat.drop_database(database_name)
        #strat.drop_user(database_user)
        return ec

    strat.list_databases()

    return 0

if __name__ == "__main__":
    import argparse
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
    parser.add_argument('--verbose', '-v', dest='verbosity', action='count', default=1,
                        help='Increase the level of output to stdout. CRITICAL and ERROR messages will always be printed.')

    args = parser.parse_args()

    logs.configure(args.verbosity)

    docker_client = docker.from_env()

    p = compose.cli.command.get_project(os.path.abspath(args.project_path), project_name=args.project_name)

    try:
        if args.setup_catalog:
            logging.debug('setting up catalog [{}]'.format(p.name))
            ec = setup_catalog(docker_client, p.name, args.database)

            if ec is not 0:
                exit(ec)

    except Exception as e:
        logging.critical(e)

        raise

