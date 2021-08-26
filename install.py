# grown-up modules
import compose.cli.command
import docker
import logging
import os

# local modules
import context
import execute

def platform_upgrade_command(platform):
    if 'centos' in platform:
        return 'rpm -U --force'
    elif 'ubuntu' in platform:
        return 'apt install -fy'
    else:
        raise RuntimeError('unsupported platform [{}]'.format(platform))

def package_filename_extension(platform):
    if 'centos' in platform:
        return 'rpm'
    elif 'ubuntu' in platform:
        return 'deb'
    else:
        raise RuntimeError('unsupported platform [{}]'.format(platform))

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

def install_package_on_container(docker_client, docker_compose_container, packages_list, packages_tarfile_path, platform_name):
    # Only the iRODS containers need to have packages installed
    if context.is_catalog_database_container(docker_compose_container):
        return 0

    container = docker_client.containers.get(docker_compose_container.name)

    #irodsctl(container, 'stop')

    path_to_packages_in_container = put_packages_in_container(container, packages_tarfile_path)

    package_list = ' '.join([p for p in packages_list if not is_package_database_plugin(p) or context.is_catalog_service_provider_container(container)])

    cmd = ' '.join([platform_upgrade_command(platform_name), package_list])

    logging.warning('executing cmd [{0}] on container [{1}]'.format(cmd, container.name))

    ec = execute.execute_command(container, cmd)

    if ec is not 0:
        logging.error(
            'failed to install packages on container [ec=[{0}], container=[{1}]'.format(ec, c.name))

        return ec

    #irodsctl(container, 'restart')

    return 0

# TODO: Want to make a more generic version of this
def install_irods_packages(docker_client, platform_name, database_name, package_directory, containers):
    import concurrent.futures

    package_name_list = ['irods-runtime', 'irods-icommands', 'irods-server', 'irods-database-plugin-{}'.format(database_name)]

    packages = get_list_of_package_paths(platform_name, package_directory, package_name_list)

    logging.info('packages to install [{}]'.format(packages))

    # TODO: output directory should contain the tarfile of packages for archaeological purposes
    tarfile_path = create_tarfile(packages)

    rc = 0
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures_to_containers = {executor.submit(install_package_on_container, docker_client, c, packages, tarfile_path, platform_name): c for c in containers}
        logging.debug(futures_to_containers)

        for f in concurrent.futures.as_completed(futures_to_containers):
            container = futures_to_containers[f]
            try:
                ec = f.result()
                if ec is not 0:
                    logging.error('error while installing packages on container [{}]'.format(container.name))
                    rc = ec

                logging.info('packages installed successfully [{}]'.format(container.name))

            except Exception as e:
                logging.error('exception raised while installing packages [{}]'.format(container.name))
                logging.error(e)
                rc = 1

    return rc


if __name__ == "__main__":
    import argparse
    import logs

    parser = argparse.ArgumentParser(description='Install iRODS packages from a local directory to a docker-compose project.')
    parser.add_argument('project_path', metavar='PROJECT_PATH', type=str,
                        help='Path to the docker-compose project on which packages will be installed.')
    parser.add_argument('package_directory', metavar='PATH_TO_DIRECTORY_WITH_PACKAGES', type=str,
                        help='Path to local directory which contains iRODS packages to be installed.')
    parser.add_argument('--project-name', metavar='PROJECT_NAME', type=str, dest='project_name',
                        help='Name of the docker-compose project on which to install packages.')
    parser.add_argument('--os-platform-tag', '-p', metavar='OS_PLATFORM_IMAGE_TAG', dest='platform', type=str, default='ubuntu:18.04',
                        help='The tag of the base Docker image to use (e.g. centos:7)')
    parser.add_argument('--database-tag', '-d', metavar='DATABASE_IMAGE_TAG', dest='database', type=str, default='postgres:10.12',
                        help='The tag of the database container to use (e.g. postgres:10.12')
    parser.add_argument('--verbose', '-v', dest='verbosity', action='count', default=1,
                        help='Increase the level of output to stdout. CRITICAL and ERROR messages will always be printed.')

    args = parser.parse_args()

    logs.configure(args.verbosity)

    p = compose.cli.command.get_project(os.path.abspath(args.project_path), project_name=args.project_name)

    if len(p.containers()) is 0:
        logging.critical(
            'no containers found for project [directory=[{0}], name=[{1}]]'.format(
            os.path.abspath(args.project_path), args.project_name))

        exit(1)

    logging.debug('containers on project [{}]'.format([c.name for c in p.containers()]))

    exit(
        install_irods_packages(
            docker.from_env(),
            context.image_name(args.platform),
            context.image_name(args.database),
            os.path.abspath(args.package_directory),
            p.containers()
        )
    )

