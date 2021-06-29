# irods\_test

This repo provides a series of docker-compose files which are intended for use in a test framework which may or may not exist at the time of writing.

The most basic setup for running the iRODS test would be a Catalog Service Provider and a database container for holding the catalog.

In this repository, the most basic set up is as follows:
 - Database container (custom built in order to populate catalog tables)
 - Catalog Service Provider
 - 3 Catalog Service Consumers
    - Each is aliased within the docker network to be recognizable in a manner expected by the tests

To run the tests, the following steps must be performed:

Stand up the topology
```
$ docker-compose up
```

Run the tests while pointed at the container using run\_tests.py
```
# runs the entire test suite on the CSP as if it were not in a topology (i.e. "core tests")
$ docker exec --user irods --workdir /var/lib/irods irods_test_base_irods-catalog-provider1_1 python ./scripts/run_tests.py --run_python_suite

# runs specific test module on the CSC (i.e. "topology from resource")
$ docker exec --user irods --workdir /var/lib/irods irods_test_base_irods-catalog-consumer-resource1_1 python ./scripts/run_tests.py --topology=resource --run_s test_ils
```

Tear down the topology (removes containers!)
```
$ docker-compose down
```

The latest version of iRODS available in the repository for the given platform is installed by default.
Custom packages can be installed manually but in the future this should be more automated and allow for specifying versions.

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
