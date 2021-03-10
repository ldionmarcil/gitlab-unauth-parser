# gitlab-unauth-parser
Parses interesting Gitlab v4 unauthenticated APIs to extract useful information such as:
- Public Repositories
- Users
- Groups

### Usage
```
$ poetry run python -m gitlab_unauth_parser -h
usage: gitlab_unauth_parser.py [-h] [-u URL] [-f] [-c CLONE] [-w WRITE]

optional arguments:
  -h, --help            show this help message and exit
  -u URL, --url URL     URL containing the Gitlab instance
  -f, --fingerprint     Don't try to detect valid Gitlab instance
  -c CLONE, --clone CLONE
                        Repository to clone projects to. Will not clone if unspecified
  -w WRITE, --write WRITE
                        Write output to file (repos.txt, groups.txt, users.txt)
```

Example: `$ poetry run python -m gitlab_unauth_parser -u https://gitlab.gnome.org/ -c /tmp/foobar`

### Purpose
#### Repositories
Unbeknownst to many Gitlab administrators, "public" repositories do not mean "public to the organization". They mean public to all, even if the Gitlab instance has no public registration. Using the Gitlab API, it is possible to find these repositories and then clone them.
#### Users
The Gitlab user API starts at user ID `1` and is incremented by 1 for each user. With this knowledge, this script starts at the begining and requests user IDs until 20 subsequent user IDs are not found, indicating that the last user has likely been found. Using this, we can extract the list of users of some Gitlab instances without authentication.
#### Groups
Groups can help understand the kind of data this Gitlab instance is responsible for hosting.
