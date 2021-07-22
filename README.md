# irods\_test

This repo provides a series of docker-compose files which are intended for use in a test framework which may or may not exist at the time of writing.

The most basic setup for running the iRODS test would be a Catalog Service Provider and a database container for holding the catalog.

In this repository, the most basic set up is as follows:
 - Database container (custom built in order to populate catalog tables)
 - Catalog Service Provider
 - 3 Catalog Service Consumers
    - Each is aliased within the docker network to be recognizable in a manner expected by the tests

Any docker-compose project can be substituted/added for support so long as it meets the requirements for running iRODS tests (i.e. additional OS/DB support).

## Running tests on a project

Each docker-compose project is actually just running iRODS servers in containers which are held in existence by an infinite loop. Anything can be run on any container in the topology.

To run the tests, the following steps must be performed:

1. Stand up the topology
```
docker-compose up
```
The above assumes the working directory holds the docker-compose.yml file for the particular OS/DB configuration you want. If you want to run from a different project, try this:
```
docker-compose --project-directory <full or relative path to directory with docker-compose.yml> up
```

2. Run the tests while pointed at the container using run\_tests.py. Examples:
```
# runs the entire test suite with ubuntu:18.04 and postgres:10.12 on the CSP as if it were not in a topology (i.e. "core tests")
docker exec --user irods --workdir /var/lib/irods ubuntu-18.04-postgres-10.12_irods-catalog-provider1_1 python ./scripts/run_tests.py --run_python_suite

# runs specific test module with centos:7 and mysql:5.7 on the CSC (i.e. "topology from resource")
docker exec --user irods --workdir /var/lib/irods centos-7-mysql-5.7_irods-catalog-consumer-resource1_1 python ./scripts/run_tests.py --topology=resource --run_s test_ils
```

3. Tear down the topology (removes containers!)
```
docker-compose down
```

The latest version of iRODS available in the repository for the given platform is installed by default.
Custom packages can be installed manually but in the future this should be more automated and allow for specifying versions.

## run\_irods\_test.py

This script allows you to specify a platform docker image tag (OS), a database docker image tag, and a location from which to install built iRODS packages and then performs the following steps:

1. Locates the project indicated by the choice of platform and database by transforming the docker image names and tags into a hyphen-delimited string which should match an existing directory which should house a docker-compose project.
 - For example, if the provided platform image tag is ubuntu:18.04 and the provided database image tag is postgres:10.12, the docker-compose project should be: `./projects/ubuntu-18.04-postgres-10.12`
2. The docker-compose project is brought up (i.e. `docker-compose up`)
 - The docker-compose projects are composed of 5 containers with these "base" names:
   1. irods-catalog-provider
   2. irods-catalog-consumer1
   3. irods-catalog-consumer2
   4. irods-catalog-consumer3
   5. icat
 - The docker image tags generated by the docker-compose projects prepend the docker-compose project string to the "base" name
   - For example, if the provided platform image tag is ubuntu:18.04 and the provided database image tag is postgres:10.12, the docker image tag for irods-catalog-consumer2 should be: `ubuntu-18.04-postgres-10.12_irods-catalog-consumer2`
3. If specified, custom packages are installed on each of the iRODS containers
 - The custom packages are located at the specified location
 - Added to a .tar file on the host machine
 - Copied and unpacked into each container at an identical path as the host machine (i.e. `docker cp`) 
 - Installed on each container using the appropriate package manager for the selected platform
4. The list of commands are run in sequence on the specified container (i.e. `docker exec <--run-on-container>`)
5. The contents of `/var/lib/irods/log` are copied out of each container into a .tar file in the `--output-directory`
6. The docker-compose project is brought down (i.e. `docker-compose down` - removes containers)

Example usage:
```
# runs specific test module on the CSC (i.e. "topology from resource")
python run_tests_in_zone.py --run-on-container irods-catalog-consumer-resource1 'python ./scripts/run_tests.py --topology=resource --run_s test_ils.Test_Ils.test_option_d_with_collections__issue_5506'
```
`--run-on-container` should be the "base" name for the container on which the command given should be executed. The specific project information and container instance information will be programmatically added in the script.

## Thanks

Thanks to @korydraughn for the [reference implementations](https://github.com/korydraughn/irods_docker/tree/master/compose/just_stand_it_up)

Thanks to @trel for the [package generation model](https://github.com/trel/build_and_sync_apt_and_yum_repositories)
