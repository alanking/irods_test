import argparse
import docker
import execute_on_project

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run iRODS tests in a consistent environment.')
    parser.add_argument('command', metavar='COMMAND', type=str,
                        help='The string representing the command to be run in the container')
    parser.add_argument('--container', metavar='CONTAINER', type=str,
                        default='irods_test_base_irods-catalog-provider_1',
                        help='The name of the container on which the command will run')
    #parser.add_argument('--platform', metavar='PLATFORM', type=str,
                        #help='The tag of the base Docker image to use (e.g. centos:7)')
    #parser.add_argument('--database', metavar='DATABASE', type=str,
                        #help='The tag of the database container to use (e.g. postgres:10.12')

    args = parser.parse_args()

    # TODO: modify project name based on selected platform and DB
    project_name = 'irods_test_base'

    exit(execute_on_project.execute_on_project(project_name, args.container, args.command, docker.from_env()))
