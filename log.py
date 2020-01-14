import jsonpickle

import config


def log(update):
    with open(config.path_log, 'a') as file:
        file.write(
            jsonpickle.encode(update) + '\n'
        )


def error(update, err):
    with open(config.path_err, 'a') as file:
        file.write(
            jsonpickle.encode(update) + '\n'
            + jsonpickle.encode(err) + '\n'
        )


def read_log():
    with open(config.path_log, 'r') as file:
        for line in file:
            yield jsonpickle.decode(line)
