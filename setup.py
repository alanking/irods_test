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
    logging.warning('setting up catalog [{}]'.format(project_name))

    container_name = context.irods_catalog_database_container(project_name, service_instance)

    container = docker_client.containers.get(container_name)

    strat = make_database_setup_strategy(database_tag, container)

    ec = strat.create_database(database_name)
    if ec is not 0:
        raise RuntimeError('failed to create database [{}]'.format(database_name))

    ec = strat.create_user(database_user, database_password)
    if ec is not 0:
        raise RuntimeError('failed to create user [{}]'.format(database_user))

    ec = strat.grant_privileges(database_name, database_user)
    if ec is not 0:
        raise RuntimeError('failed to grant privileges to user [{0}] on database [{1}]'.format(database_user, database_name))

    strat.list_databases()

class setup_input_builder(object):
    def __init__(self):
        self.service_account_name = ''
        self.service_account_group = ''
        self.catalog_service_role = ''

        self.odbc_driver = ''
        self.database_server_hostname = 'localhost'
        self.database_server_port = 5432
        self.database_name = 'ICAT'
        self.database_username = 'irods'
        self.database_password = 'testpassword'
        self.stored_passwords_salt = ''

        self.zone_name = 'tempZone'
        self.zone_port = 1247
        self.parallel_port_range_begin = 20000
        self.parallel_port_range_end = 20199
        self.control_plane_port = 1248
        self.schema_validation_base_uri = ''
        self.admin_username = 'rods'

        self.zone_key = 'TEMPORARY_ZONE_KEY'
        self.negotiation_key = '32_byte_server_negotiation_key__'
        self.control_plane_key = '32_byte_server_control_plane_key'
        self.admin_password = 'rods'

        self.vault_directory = ''

        self.catalog_service_provider_host = 'localhost'

    def service_account(self,
                        service_account_name='',
                        service_account_group='',
                        catalog_service_role=''):
        self.service_account_name = service_account_name
        self.service_account_group = service_account_group
        self.catalog_service_role = catalog_service_role

        return self


    def database_connection(self,
                            odbc_driver='',
                            database_server_hostname='localhost',
                            database_server_port=5432,
                            database_name='ICAT',
                            database_username='irods',
                            database_password='testpassword',
                            stored_passwords_salt=''):
        self.odbc_driver = odbc_driver
        self.database_server_hostname = database_server_hostname
        self.database_server_port = database_server_port
        self.database_name = database_name
        self.database_username = database_username
        self.database_password = database_password
        self.stored_passwords_salt = stored_passwords_salt

        return self


    def server_options(self,
                       zone_name='tempZone',
                       catalog_service_provider_host='localhost',
                       zone_port=1247,
                       parallel_port_range_begin=20000,
                       parallel_port_range_end=20199,
                       control_plane_port=1248,
                       schema_validation_base_uri='',
                       admin_username='rods'):
        self.zone_name = zone_name
        self.catalog_service_provider_host = catalog_service_provider_host
        self.zone_port = zone_port
        self.parallel_port_range_begin = parallel_port_range_begin
        self.parallel_port_range_end = parallel_port_range_end
        self.control_plane_port = control_plane_port
        self.schema_validation_base_uri = schema_validation_base_uri
        self.admin_username = admin_username

        return self


    def keys_and_passwords(self,
                           zone_key = 'TEMPORARY_ZONE_KEY',
                           negotiation_key = '32_byte_server_negotiation_key__',
                           control_plane_key = '32_byte_server_control_plane_key',
                           admin_password = 'rods'):
        self.zone_key = zone_key
        self.negotiation_key = negotiation_key
        self.control_plane_key = control_plane_key
        self.admin_password = admin_password

        return self


    def vault_directory(self, vault_directory=''):
        self.vault_directory = vault_directory

        return self


    def build_input_for_catalog_consumer(self):
        # The setup script defaults catalog service consumer option as 2
        role = 2
        return '\n'.join([
            str(self.service_account_name),
            str(self.service_account_group),
            str(role),

            str(self.zone_name),
            str(self.catalog_service_provider_host),
            str(self.zone_port),
            str(self.parallel_port_range_begin),
            str(self.parallel_port_range_end),
            str(self.control_plane_port),
            str(self.schema_validation_base_uri),
            str(self.admin_username),
            'y', # confirmation of inputs

            str(self.zone_key),
            str(self.negotiation_key),
            str(self.control_plane_key),
            str(self.admin_password),
            '', #confirmation of inputs

            str(self.vault_directory),
            '' # confirmation of inputs
        ])

    def build_input_for_catalog_provider(self):
        role = ''
        return '\n'.join([
            str(self.service_account_name),
            str(self.service_account_group),
            str(role),

            str(self.odbc_driver),
            str(self.database_server_hostname),
            str(self.database_server_port),
            str(self.database_name),
            str(self.database_username),
            'y', # confirmation of inputs
            str(self.database_password),
            str(self.stored_passwords_salt),

            str(self.zone_name),
            str(self.zone_port),
            str(self.parallel_port_range_begin),
            str(self.parallel_port_range_end),
            str(self.control_plane_port),
            str(self.schema_validation_base_uri),
            str(self.admin_username),
            'y', # confirmation of inputs

            str(self.zone_key),
            str(self.negotiation_key),
            str(self.control_plane_key),
            str(self.admin_password),
            '', # confirmation of inputs

            str(self.vault_directory),
            '' # final confirmation
        ])

    def build(self):
        build_for_role = {
            'provider': self.build_input_for_catalog_provider,
            'consumer': self.build_input_for_catalog_consumer
        }

        try:
            return build_for_role[self.catalog_service_role]()

        except KeyError:
            raise NotImplementedError('unsupported catalog service role [{}]'.format(self.catalog_service_role))


def setup_irods_server(container, setup_input):
    ec = execute.execute_command(container, 'bash -c \'echo "{}" > /input\''.format(setup_input))
    if ec is not 0:
        raise RuntimeError('failed to create setup script input file [{}]'.format(container.name))

    execute.execute_command(container, 'cat /input')

    path_to_setup_script = os.path.join('/var', 'lib', 'irods', 'scripts', 'setup_irods.py')
    run_setup_script = 'bash -c \'python {0} < /input\''.format(path_to_setup_script)
    ec = execute.execute_command(container, run_setup_script)
    if ec is not 0:
        raise RuntimeError('failed to set up iRODS catalog service provider [{}]'.format(container.name))

    ec = execute.execute_command(container, '/var/lib/irods/irodsctl -v start', user='irods')
    if ec is not 0:
        raise RuntimeError('failed to start iRODS server after setup [{}]'.format(container.name))


def setup_irods_catalog_provider(docker_client, project_name, database_service_instance=1, provider_service_instance=1):
    db_container_name = context.irods_catalog_database_container(project_name, provider_service_instance)
    db_container = docker_client.containers.get(db_container_name)

    setup_input = (setup_input_builder()
                    .service_account(catalog_service_role='provider')
                    .database_connection(database_server_hostname=context.container_hostname(db_container))
                    .build())

    logging.debug('input to setup script [{}]'.format(setup_input))

    csp_container_name = context.irods_catalog_provider_container(project_name, provider_service_instance)
    csp_container = docker_client.containers.get(csp_container_name)

    logging.warning('setting up iRODS catalog provider [{}]'.format(csp_container_name))

    setup_irods_server(csp_container, setup_input)


def setup_irods_catalog_consumer(docker_client, project_name, provider_service_instance=1, consumer_service_instance=1):
    csp_container_name = context.irods_catalog_provider_container(project_name, provider_service_instance)
    csp_container = docker_client.containers.get(csp_container_name)

    setup_input = (setup_input_builder()
                    .service_account(catalog_service_role='consumer')
                    .server_options(catalog_service_provider_host=context.container_hostname(csp_container))
                    .build())

    logging.debug('input to setup script [{}]'.format(setup_input))

    csc_container_name = context.irods_catalog_consumer_container(project_name, consumer_service_instance)
    csc_container = docker_client.containers.get(csc_container_name)

    logging.warning('setting up iRODS catalog consumer [{}]'.format(csc_container_name))

    setup_irods_server(csc_container, setup_input)


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
            setup_catalog(docker_client, p.name, args.database)

        if args.setup_irods_catalog_provider:
            setup_irods_catalog_provider(docker_client, p.name)

        # TODO: parallel!
        for i in range(args.irods_catalog_consumer_count):
            # range() is 0-based, so add 1 to match the service instance numbering scheme of docker-compose
            setup_irods_catalog_consumer(docker_client, p.name, consumer_service_instance=i + 1)

    except Exception as e:
        logging.critical(e)
        raise

