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

