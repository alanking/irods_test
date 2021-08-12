import container
import docker
import logging
import os

# TODO: Maybe this should be some kind of builder
def configure(verbosity=1, log_filename=None):
    # CRITICAL messages will always be printed, but anything after that is a function of the number of -v
    level = logging.CRITICAL - 10 * verbosity

    handlers = [logging.StreamHandler()]

    if log_filename:
        handlers.append(logging.FileHandler(os.path.abspath(log_filename)))

    logging.basicConfig(
        level = level if level > logging.NOTSET else logging.DEBUG,
        format = '%(asctime)-15s %(levelname)s - %(message)s',
        handlers = handlers
    )

def collect_logs(docker_client, containers, output_directory, logfile_path='/var/lib/irods/log'):
    od = os.path.join(output_directory, 'logs')
    if not os.path.exists(od):
        os.makedirs(od)

    for c in containers:
        if container.is_catalog_database_container(c): continue

        log_archive_path = os.path.join(od, c.name)

        logging.info('saving log [{}]'.format(log_archive_path))

        try:
            # TODO: get server version to determine path of the log files
            bits, _ = docker_client.containers.get(c.name).get_archive(logfile_path)

            with open(log_archive_path, 'wb') as f:
                for chunk in bits:
                    f.write(chunk)

        except Exception as e:
            logging.error('failed to collect log [{}]'.format(log_archive_path))
            logging.error(e)
