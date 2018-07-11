#!/usr/bin/env python3

import re

from pathlib import Path


def make_index():
    base_dir = Path.cwd()
    readme = base_dir / 'README.md'

    sub_dirs = sorted([_dir for _dir in base_dir.iterdir() if _dir.is_dir()])

    with readme.open('w') as f:
        f.write('{}\n\n'.format(md_h('INDEX')))

        for _dir in sub_dirs:
            dir_name = get_dir_name(_dir)
            if ignore_dir(dir_name):
                continue

            f.write('{}\n\n'.format(md_h(dir_name, 2)))

            notes = sorted([note for note in _dir.iterdir() if note.is_file()])
            for note in notes:
                name = note.name
                path = get_relative_path(base_dir, note)
                f.write('{}\n'.format(md_list(md_link(name, path))))

            f.write('\n')


def get_dir_name(path):
    return str(path).split('/')[-1]


def ignore_dir(dir_name):
    pattern = re.compile('\.')
    return pattern.match(dir_name)


def get_relative_path(base, abspath):
    base = str(base)
    abspath = str(abspath)
    relative_path = '.' + abspath[len(base):]

    return relative_path


def md_link(name, path):
    path = '%20'.join(path.split(' '))
    return '[{}]({})'.format(name, path)


def md_h(head, level=1):
    return '{} {}'.format('#' * level, head)


def md_list(list):
    return '- {}'.format(list)


if __name__ == '__main__':
    make_index()
