# grown-up modules
import compose.cli.command
import docker
import logging
import os

# local modules
import context
import database_setup
import execute
import install
import irods_setup

def job_name(project_name, prefix=None):
    """Construct unique job name based on the docker-compose project name.

    The job name returned will be of the form: `project_name`_`prefix`_`uuid.uuid4()`

    If no `prefix` is provided, the job name will be of the form: `project_name`_`uuid.uuid4()`

    Arguments:
    project_name -- docker-compose project name which identifies the type of test being run
    prefix -- optional prefix for the job name
    """
    import uuid
    # TODO: use timestamps, also
    if prefix:
        return '_'.join([prefix, project_name, str(uuid.uuid4())])

    return '_'.join([project_name, str(uuid.uuid4())])


def make_output_directory(dirname, basename):
    """Create a directory for job output and return its full path.

    Arguments:
    dirname -- base directory in which the unique subdirectory for output will be created
    basename -- unique subdirectory which will be created under the provided dirname
    """
    p = os.path.join(os.path.abspath(dirname), basename)

    try:
        os.makedirs(p)
    except OSError as e:
        if e.errno != errno.EEXIST or not os.path.isdir(p):
            raise

    return p


def configure_irods_testing(docker_client, containers):
    # Make sure univMSS interface is configured for testing
    path_to_univmss_script = os.path.join('/var', 'lib', 'irods', 'msiExecCmd_bin', 'univMSSInterface.sh')
    chown_msiexec_directory = 'chown irods:irods {}'.format(os.path.dirname(path_to_univmss_script))
    copy_from_template = 'cp {0}.template {0}'.format(path_to_univmss_script)
    remove_template_from_commands = 'sed -i \"s/template-//g\" {}'.format(path_to_univmss_script)
    make_script_executable = 'chmod 544 {}'.format(path_to_univmss_script)

    for container in containers:
        if context.is_catalog_database_container(container): continue

        c = docker_client.containers.get(container.name)
        if execute.execute_command(c, chown_msiexec_directory) is not 0:
            raise RuntimeError('failed to change ownership to msiExecCmd_bin')
        if execute.execute_command(c, copy_from_template, user='irods', workdir='/var/lib/irods') is not 0:
            raise RuntimeError('failed to copy univMSSInterface.sh template file')
        if execute.execute_command(c, remove_template_from_commands, user='irods', workdir='/var/lib/irods') is not 0:
            raise RuntimeError('failed to modify univMSSInterface.sh template file')
        if execute.execute_command(c, make_script_executable, user='irods', workdir='/var/lib/irods') is not 0:
            raise RuntimeError('failed to change permissions on univMSSInterface.sh')

if __name__ == "__main__":
    import argparse
    import logs

    parser = argparse.ArgumentParser(description='Run iRODS tests in a consistent environment.')
    parser.add_argument('commands', metavar='COMMANDS', nargs='+',
                        help='Space-delimited list of commands to be run')
    parser.add_argument('--project-directory', metavar='PATH_TO_PROJECT_DIRECTORY', type=str, dest='project_directory', default='.',
                        help='Path to the docker-compose project on which packages will be installed.')
    parser.add_argument('--project-name', metavar='PROJECT_NAME', type=str, dest='project_name',
                        help='Name of the docker-compose project on which to install packages.')
    parser.add_argument('--run-on-service-instance', '-t', metavar='TARGET_SERVICE_INSTANCE', dest='run_on', type=str, nargs=2, default='irods-catalog-provider 1',
                        help='The service instance on which the command will run represented as "SERVICE_NAME SERVICE_INSTANCE_NUM".')
    parser.add_argument('--output-directory', '-o', metavar='FULLPATH_TO_DIRECTORY_FOR_OUTPUT', dest='output_directory', type=str,
                        help='Full path to local directory for output from execution.')
    parser.add_argument('--os-platform-tag', '-p', metavar='OS_PLATFORM_IMAGE_TAG', dest='platform', type=str,
                        help='The tag of the base Docker image to use')
    parser.add_argument('--database-tag', '-d', metavar='DATABASE_IMAGE_TAG', dest='database', type=str,
                        help='The tag of the database container to use')
    parser.add_argument('--job-name', '-j', metavar='JOB_NAME', dest='job_name', type=str,
                        help='Name of the test run')
    parser.add_argument('--package-directory', metavar='PATH_TO_DIRECTORY_WITH_PACKAGES', type=str, dest='package_directory',
                        help='Path to local directory which contains iRODS packages to be installed')
    parser.add_argument('--package-version', metavar='PACKAGE_VERSION_TO_DOWNLOAD', type=str, dest='package_version',
                        help='Version of iRODS to download and install')
    parser.add_argument('--verbose', '-v', dest='verbosity', action='count', default=1,
                        help='Increase the level of output to stdout. CRITICAL and ERROR messages will always be printed.')

    args = parser.parse_args()

    if args.package_directory and args.package_version:
        print('package directory and package version are mutually exclusive')
        exit(1)

    # Get the context for the Compose file
    project_directory = os.path.abspath(args.project_directory)
    p = compose.cli.command.get_project(project_directory, project_name=args.project_name)

    project_name = args.project_name if args.project_name else p.name

    job_name = job_name(p.name, args.job_name)

    if args.output_directory:
        dirname = args.output_directory
    else:
        import tempfile
        dirname = tempfile.mkdtemp(prefix=project_name)

    output_directory = make_output_directory(dirname, job_name)

    logs.configure(args.verbosity, os.path.join(output_directory, 'script_output.log'))

    # Derive the platform image tag if it is not provided
    if args.platform:
        platform = args.platform
        logging.debug('provided platform image tag [{}]'.format(platform))
    else:
        platform = context.platform_image_repo_and_tag(project_name)
        logging.debug('derived platform image tag [{}]'.format(platform))

    # Derive the database image tag if it is not provided
    if args.database:
        database = args.database
        logging.debug('provided database image tag [{}]'.format(database))
    else:
        database = context.database_image_repo_and_tag(project_name)
        logging.debug('derived database image tag [{}]'.format(database))

    ec = 0
    containers = list()
    docker_client = docker.from_env()

    try:
        # Bring up the services
        logging.debug('bringing up project [{}]'.format(p.name))
        consumer_count = 3
        containers = p.up(scale_override={context.irods_catalog_consumer_service(): consumer_count})

        # Install iRODS packages
        if args.package_directory:
            logging.warning('installing iRODS packages from directory [{}]'
                            .format(args.package_directory))

            install.install_local_irods_packages(docker_client,
                                                 context.image_repo(platform),
                                                 context.image_repo(database),
                                                 args.package_directory,
                                                 containers)
        else:
            # Even if no version was provided, we default to using the latest official release
            logging.warning('installing official iRODS packages [{}] (empty == latest release)'
                            .format(args.package_version))

            install.install_official_irods_packages(docker_client,
                                                    context.image_repo(platform),
                                                    context.image_repo(database),
                                                    args.package_version,
                                                    containers)

        database_setup.setup_catalog(docker_client, project_name, p.containers(), database)

        irods_setup.setup_irods_catalog_provider(docker_client, p.name)

        irods_setup.setup_irods_catalog_consumers(docker_client, p)

        # Configure the containers for running iRODS automated tests
        logging.info('configuring iRODS containers for testing')
        configure_irods_testing(docker_client, containers)

        # Get the container on which the command is to be executed
        logging.debug('--run-on-service-instance [{}]'.format(args.run_on.split()))
        target_service_name, target_service_instance = args.run_on.split()
        container = docker_client.containers.get(context.container_name(p.name, target_service_name, target_service_instance))
        logging.debug('got container to run on [{}]'.format(container.name))

        # Serially execute the list of commands provided in the input
        for command in list(args.commands):
            # TODO: on --continue, save only failure ec's/commands
            ec = execute.execute_command(container, command, user='irods', workdir='/var/lib/irods', stream_output=True)

    except Exception as e:
        logging.critical(e)

        raise

    finally:
        logging.warning('collecting logs [{}]'.format(output_directory))
        logs.collect_logs(docker_client, containers, output_directory)

        p.down(include_volumes = True, remove_image_type = False)

    exit(ec)
