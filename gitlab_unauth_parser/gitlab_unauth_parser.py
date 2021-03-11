import argparse
import concurrent.futures
import logging
import os
from sys import exit, stdout

import git
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PROJECTS_API = '/api/v4/projects'
USERS_API = '/api/v4/users'
GROUPS_API = '/api/v4/groups'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-u',
                        '--url',
                        help="URL containing the Gitlab instance")

    parser.add_argument('-f',
                        '--fingerprint',
                        action='store_false',
                        default=True,
                        help="Don't try to detect valid Gitlab instance")

    parser.add_argument(
        '-c',
        '--clone',
        type=str,
        help="Repository to clone projects to. Will not clone if unspecified")

    parser.add_argument(
        '-w',
        '--write',
        type=str,
        help="Write output to file (repos.txt, groups.txt, users.txt)")

    args = parser.parse_args()

    # setup loggers
    logging.basicConfig(level=logging.INFO, format='%(message)s')

    def setup_logger(name):
        file_handler = logging.FileHandler(f'{name}.txt')
        file_handler.setFormatter(logging.Formatter('%(message)s'))

        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        logger.addHandler(file_handler)

        return logger

    setup_logger('users')
    setup_logger('projects')
    setup_logger('groups')

    g = Gitlab(args.url, args.fingerprint)
    g.get_projects(clone=args.clone)
    g.get_groups()
    g.get_users()


class Gitlab:
    url = None
    projects = []

    def __init__(self, url, fingerprint=True):
        self.url = url

        if fingerprint:
            self._is_gitlab()

    def get_projects(self, clone=False):

        logger = logging.getLogger('projects')
        res = requests.get(f'{self.url}/{PROJECTS_API}', verify=False)
        projects = res.json()
        repos = []

        logging.info(f'Found {len(projects)} public projects.')
        for project in projects:
            namespace = project['namespace']['path']
            name = project['name']
            description = project['description']
            stars = project['star_count']
            created = project['created_at']
            last_activity = project['last_activity_at']
            http_url = project['http_url_to_repo']
            url = project['web_url']

            logger.info(f'  - Name: {name} ({stars} stars) {url}')
            if description:
                logger.info(f'  - Description: {description}')
            logger.info(
                f'  - Created: {created} (Last updated {last_activity})')
            logger.info('')

            if clone:
                repos.append((
                    namespace,
                    http_url,
                ))

        # clone repos if we found any
        if repos:

            def clone_repo(namespace, repo_url):
                clone_dir = f'{clone}/{namespace}'
                os.makedirs(clone_dir, exist_ok=True)
                git.Git(clone_dir).clone(repo_url)

            with concurrent.futures.ThreadPoolExecutor(
                    max_workers=15) as executor:
                future_to_repo = {
                    executor.submit(clone_repo, namespace, repo):
                    (namespace, repo)
                    for namespace, repo in repos
                }

                logging.info(
                    f'Clong all {len(repos)} repositories to {clone}. Could take a while!'
                )
                for future in concurrent.futures.as_completed(future_to_repo):
                    stdout.write('.')
                    stdout.flush()

                logging.info('Done')
                logging.info('')

    def get_users(self):

        logger = logging.getLogger('users')
        id = 1
        buffer = 20
        last_user_found = 1

        logger.info('Enumerating users...')
        while True:
            res = requests.get(f'{self.url}/{USERS_API}/{id}', verify=False)

            if res.status_code == 200:
                last_user_found = id
                user = res.json()

                name = user['name']
                username = user['username']
                state = user['state']

                logger.info(f'  - {username} ({name}) [{state}]')

            id += 1
            # user not found, been too long since we've observed a valid user
            if res.status_code != 200 and (id - last_user_found) > buffer:
                logger.info(
                    f'More than {buffer} IDs not found since last user found, stopping.'
                )
                break

    def get_groups(self):

        logger = logging.getLogger('groups')
        res = requests.get(f'{self.url}/{GROUPS_API}', verify=False)
        groups = res.json()

        logger.info(f'Found {len(groups)} groups.')
        for group in groups:
            full_name = group['full_name']
            description = group['description']
            created = group['created_at']
            url = group['web_url']

            logger.info(f'  - {full_name} [Created {created}]')
            if description:
                logger.info(f'  - Description: {description}')
            logger.info(f'  - URL: {url}')
            logger.info('')

    def _is_gitlab(self):
        res = requests.get(f'{self.url}/robots.txt',
                           allow_redirects=False,
                           verify=False)
        if res.status_code != 200 or 'https://gitlab.com' not in res.text:
            exit()


if __name__ == "__main__":
    main()
