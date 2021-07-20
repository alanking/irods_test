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

2. Run the tests while pointed at the container using run\_tests.py
```
# runs the entire test suite on the CSP as if it were not in a topology (i.e. "core tests")
docker exec --user irods --workdir /var/lib/irods irods_test_base_irods-catalog-provider1_1 python ./scripts/run_tests.py --run_python_suite

# runs specific test module on the CSC (i.e. "topology from resource")
docker exec --user irods --workdir /var/lib/irods irods_test_base_irods-catalog-consumer-resource1_1 python ./scripts/run_tests.py --topology=resource --run_s test_ils
```

3. Tear down the topology (removes containers!)
```
docker-compose down
```

The latest version of iRODS available in the repository for the given platform is installed by default.
Custom packages can be installed manually but in the future this should be more automated and allow for specifying versions.

## run\_irods\_test.py

The steps above have been captured in a python script called `run_irods_test.py`.

It is recommended to use a virtual environment when running this script. I'm using python 3.6.9:
```
$ pip freeze
attrs==21.2.0
bcrypt==3.2.0
cached-property==1.5.2
certifi==2021.5.30
cffi==1.14.5
chardet==4.0.0
cryptography==3.4.7
distro==1.5.0
docker==5.0.0
docker-compose==1.29.2
dockerpty==0.4.1
docopt==0.6.2
idna==2.10
importlib-metadata==4.6.0
jsonschema==3.2.0
paramiko==2.7.2
pycparser==2.20
PyNaCl==1.4.0
pyrsistent==0.18.0
python-dotenv==0.18.0
PyYAML==5.4.1
requests==2.25.1
six==1.16.0
texttable==1.6.3
typing-extensions==3.10.0.0
urllib3==1.26.6
websocket-client==0.59.0
zipp==3.4.1
```

Example usage:
```
# runs specific test module on the CSC (i.e. "topology from resource")
python run_tests_in_zone.py --run_on irods-catalog-consumer-resource1 'python ./scripts/run_tests.py --topology=resource --run_s test_ils.Test_Ils.test_option_d_with_collections__issue_5506'
```
`--run_on` should be the "generic name" for the container on which the command given should be executed. The specific project information and container instance information will be programmatically added in the script.

## Future Work
 - Copy out log files to a specified volume mount
 - Additional OS/DB support
    - Ubuntu 18.04
        - postgres
        - mysql
        - oracle
    - Ubuntu 16.04
        - postgres
        - mysql
        - oracle
    - Centos 7
        - postgres
        - mysql
        - oracle
 - Add hook for installing custom packages or a specific version
    - Ideally, the package manager for the given platform could be used on a configurable local directory or a URL
 - Create a wrapper script so this is easier to hold (e.g. `$ python run_irods_tests.py --platform ubuntu:18.04 --database postgres --topology-test from_resource`)
 - Create a series of compose files or more generic way to run plugin and client tests
 - Add support for SSL
 - Add support for upgrades
 - Add support for custom externals packages
 - Add federated zone (which is also a topology) and supports current test suite zone names and expectations
 - Allow tests to continue running after failure and only report failures (idempotency)
 - Allow tests to be retried (--retries)
    - Note: This may discourage writing resilient tests, but some of the existing tests are simply not resilient and so must be accommodated until they are resolved
 - Create a hook so that this can be used with a automation framework (e.g. Jenkins, Github Actions, etc.)
