# grown-up imports
import logging
import os

def create_archive(members):
    """Create a local archive file with the files in `members` and return a path to the file.

    Arguments:
    members -- local files to be placed in the archive
    """
    import tarfile
    import tempfile

    # TODO: allow for path to be specified
    # TODO: allow for type of archive to be specified
    # Create a tarfile with the packages
    tarfile_name = 'packages.tar'
    tarfile_path = os.path.join(tempfile.mkdtemp(), tarfile_name)

    logging.debug('creating tarfile [{}]'.format(tarfile_path))

    with tarfile.open(tarfile_path, 'w') as f:
        for m in members:
            logging.debug('adding member [{0}] to tarfile'.format(m))
            f.add(m)

    return tarfile_path

def copy_archive_to_container(container, archive_file_path_on_host, extension='.tar'):
    """Copy local archive file into the specified container in extracted form.

    Returns the absolute path inside the container where the archive file was extracted.

    Arguments:
    container -- the docker container into which the archive is being copied
    archive_file_path_on_host -- local path to the archive being copied
    """
    path = os.path.abspath(archive_file_path_on_host)
    path_to_exploded_archive_in_container = os.path.basename(path)[:len(extension) * -1]

    logging.debug('putting archive [{0}] in container [{1}] at [{2}]'.format(
        archive_file_path_on_host, container.name, path_to_exploded_archive_in_container))

    with open(archive_file_path_on_host, 'rb') as tf:
        if not container.put_archive('/', tf):
            raise RuntimeError('failed to put archive in container [{}]'.format(container.name))

    return path_to_exploded_archive_in_container

