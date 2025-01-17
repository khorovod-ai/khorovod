import json
import logging
import os
import sys
import re

import requests

# this script outputs all code files that have changed between commit and master
# environment variable GITHUB_HEAD_SHA provides the commit SHA
# environment variable GITHUB_BASE_SHA provides the master SHA

# files that match any of these regexps are considered non-code files
# even though those files have changed, they will not be in the output of this script
non_code_file_patterns = [
    r'^.buildkite/get_changed_code_files.py$',
    r'^.github/',
    r'^docs/',
    r'^docker/helm/',
    r'^.*\.md',
    r'^.*\.rst'
]


def get_changed_files(base, head):
    response = requests.get(
        'https://api.github.com/repos/khorovod-ai/khorovod/compare/{base}...{head}'.format(
            base=base, head=head
        )
    )
    if response.status_code != 200:
        logging.error('Request failed: {}'.format(json.loads(response.text).get('message')))
        return []

    compare_json = response.text
    compare = json.loads(compare_json)
    return [file.get('filename') for file in compare.get('files')]


def is_code_file(file):
    return not is_non_code_file(file)


def is_non_code_file(file):
    return any([pattern
                for pattern in non_code_file_patterns
                if re.match(pattern, file)])


if __name__ == "__main__":
    logging.getLogger().level = logging.DEBUG

    base = os.environ.get('GITHUB_BASE_SHA')
    head = os.environ.get('GITHUB_HEAD_SHA')
    if head is None or base is None:
        logging.warning('no base commit ({}) or head commit ({}) given'.format(base, head))
        sys.exit(1)

    logging.debug('base = {}'.format(base))
    logging.debug('head = {}'.format(head))

    commit_files = get_changed_files(base, head)
    if len(commit_files) == 0:
        logging.warning('could not find any commit files')
        sys.exit(1)

    changed_code_files = [file
                          for file in commit_files
                          if is_code_file(file)]
    for file in changed_code_files:
        print(file)
