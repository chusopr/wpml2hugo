#!/usr/bin/env python3
import mysql.connector
import getpass
from sys import argv, stderr
import time
from os import makedirs
import uuid
from hashlib import md5

if len(argv) != 4:
    print("Syntax: {} <hostname> <database> <user>".format(argv[0]), file=stderr)
    exit(1)

password = getpass.getpass("Password for MySQL user {} at MySQL server {} and database {}: ".format(argv[3], argv[1], argv[2]))

my = mysql.connector.connect(user=argv[3], password=password, host=argv[1], database=argv[2])

comments = my.cursor(dictionary=True)

comments.execute("""
    SELECT post_name, comment_ID, comment_author, comment_author_email, comment_author_url, comment_date_gmt, comment_content, comment_parent
    FROM wp_comments
    LEFT JOIN wp_posts
    ON ID = comment_post_ID
    WHERE
      comment_approved = 1 AND
      comment_type = ''
""")

for comment in comments:
    makedirs("comments/{}".format(comment["post_name"]), exist_ok=True)
    with open("comments/{}/entry{:.0f}000.yml".format(comment["post_name"], time.mktime(comment["comment_date_gmt"].timetuple())), "w") as f:
        f.write("""_id: {0}
replyTo: {1}
name: {2}
email: {3}
url: {4}
date: {5:.0f}
message: |
  {6}""".format(
    uuid.uuid3(uuid.NAMESPACE_DNS, str(comment["comment_ID"])),
    uuid.uuid3(uuid.NAMESPACE_DNS, str(comment["comment_parent"])) if comment["comment_parent"] != 0 else '',
    comment["comment_author"],
    md5(comment["comment_author_email"].encode()).hexdigest(),
    comment["comment_author_url"],
    time.mktime(comment["comment_date_gmt"].timetuple()),
    comment["comment_content"]
))

my.close()
