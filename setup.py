# grown-up modules
import compose.cli.command
import docker
import logging
import os

# local modules
import context
import execute

def put_packages_in_container(container, tarfile_path):
    # Copy packages tarball into container
    path_to_packages_dir_in_container = '/' + os.path.basename(tarfile_path)[:len('.tar') * -1]

    logging.debug('putting tarfile [{0}] in container [{1}] at [{2}]'.format(
        tarfile_path, container.name, path_to_packages_dir_in_container))

    with open(tarfile_path, 'rb') as tf:
        if not container.put_archive('/', tf):
            raise RuntimeError('failed to put packages archive into container [{}]'.format(container.name))

    return path_to_packages_dir_in_container


def install_package(container, platform, full_path_to_package):
    cmd = ' '.join([platform_upgrade_command(platform), full_path_to_package])

    execute.execute_command(container, cmd)

def create_tarfile(members):
    import tarfile
    import tempfile

    # Create a tarfile with the packages
    tarfile_name = 'packages.tar'
    tarfile_path = os.path.join(tempfile.mkdtemp(), tarfile_name)

    logging.debug('creating tarfile [{}]'.format(tarfile_path))

    with tarfile.open(tarfile_path, 'w') as f:
        for m in members:
            logging.debug('adding member [{0}] to tarfile'.format(m))
            f.add(m)

    return tarfile_path

def get_list_of_package_paths(platform_name, package_directory, package_name_list):
    import glob

    if not package_directory:
        raise RuntimeError('Attempting to install custom packages from unspecified location')

    package_path = os.path.abspath(package_directory)

    logging.debug('listing for [{}]:\n{}'.format(package_path, os.listdir(package_path)))

    packages = list()

    for p in package_name_list:
        p_glob = os.path.join(package_path, p + '*.{}'.format(package_filename_extension(platform_name)))

        logging.debug('looking for packages like [{}]'.format(p_glob))

        packages.append(glob.glob(p_glob)[0])

    return packages

def is_package_database_plugin(p):
    return 'database' in p

def irodsctl(container, cmd):
    execute.execute_command(container, '/var/lib/irods/irodsctl ' + cmd, user='irods')

def install_irods_packages(docker_client, platform_name, package_directory, package_name_list, containers):
    # TODO: output directory should contain the tarfile of packages for archaeological purposes
    packages = get_list_of_package_paths(platform_name, package_directory, package_name_list)

    logging.info('packages to install [{}]'.format(packages))

    tarfile_path = create_tarfile(packages)

    for c in containers:
        # Only the iRODS containers need to have packages installed
        if context.is_catalog_database_container(c): continue

        container = docker_client.containers.get(c.name)

        irodsctl(container, 'stop')

        path_to_packages_in_container = put_packages_in_container(container, tarfile_path)

        package_list = ' '.join([p for p in packages if not is_package_database_plugin(p) or context.is_catalog_service_provider_container(container)])

        cmd = ' '.join([platform_upgrade_command(platform_name), package_list])

        execute.execute_command(container, cmd)

        irodsctl(container, 'restart')

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

    dc = docker.from_env()

    base_path_to_project = os.path.join(os.path.abspath('projects'), 'base')

    path_to_project = os.path.join(base_path_to_project, args.platform, args.database)

    p = compose.cli.command.get_project(path_to_project, project_name=args.project)

    setup_catalog(dc, p.name)

