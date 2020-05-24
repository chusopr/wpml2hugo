#!/usr/bin/env python3
import mysql.connector
import getpass
from sys import argv, stderr
from os import makedirs

if len(argv) != 4:
    print("Syntax: {} <hostname> <database> <user>".format(argv[0]), file=stderr)
    exit(1)

password = getpass.getpass("Password for MySQL user {} at MySQL server {} and database {}: ".format(argv[3], argv[1], argv[2]))

my = mysql.connector.connect(user=argv[3], password=password, host=argv[1], database=argv[2])

posts = my.cursor(dictionary=True, buffered=True)

"""
  Getting all content with their corresponding translations alltogether with
  one single MySQL query turned out to be too complex because not all content
  is translated and MySQL lacks support for OUTER JOIN, which turned out in a
  big and complex SELECT UNION as shown in tags.py.

  Instead, here I will be just fetching all languages separately and match the
  content with its translations on Python side.

  If you are not using WPML, you just need to remove the JOIN part, the trid and
  language_code from the SELECT clause and all the translation stuff from the
  for loop.
"""

posts.execute("""
SELECT ID, post_date_gmt, post_content, post_title, post_status, post_modified_gmt, post_name, post_type, trid, language_code FROM wp_posts
LEFT JOIN wp_icl_translations
ON
  wp_posts.id = wp_icl_translations.element_id AND
  wp_icl_translations.element_type = CONCAT('post_', post_type)
WHERE
  (post_type = 'page' OR post_type = 'post') AND
  (post_status = 'draft' OR post_status = 'publish')
""")

post_data = my.cursor(dictionary=True, buffered=True)
post_data2 = my.cursor(dictionary=True, buffered=True)

for post in posts:
    if post["language_code"] == "es":
        # If present, English slugs are used for filenames in both languages
        # That's the simplest way for Hugo to know they are translations
        # So we need to search for the English translation of this content
        post_data.execute("SELECT post_name FROM wp_icl_translations JOIN wp_posts on ID = element_id WHERE trid = {} AND element_id != {}".format(post["trid"], post["ID"]))
        translation = post_data.fetchall()
        if post_data.rowcount == 1:
            filename = translation[0]["post_name"]
        elif post_data.rowcount == 0:
            filename = post["post_name"]
        else:
            raise Exception("That was unexpected") # Unless you have more than two languages
    else:
        filename = post["post_name"]

    if post["post_type"] == "post" and post["post_date_gmt"]:
        makedirs("posts/{}/{}".format(post["post_date_gmt"].year, post["post_date_gmt"].month), exist_ok=True)
        filename = "posts/{}/{}/{}.{}.html".format(post["post_date_gmt"].year, post["post_date_gmt"].month, filename, post["language_code"])
    else:
        filename = "documents/{}.{}.html".format(filename, post["language_code"])

    with open(filename, "w") as f:
        f.write("---\n")
        if post["post_title"]:
            f.write("title: \"{}\"\n".format(post["post_title"]))
        if post["post_status"] != "publish":
            f.write("draft: True\n")
        if post["post_date_gmt"]:
            f.write("date: {}+00:00\n".format(post["post_date_gmt"].isoformat()))
        if post["post_modified_gmt"] and post["post_modified_gmt"] != post["post_date_gmt"]:
            f.write("lastmod: {}+00:00\n".format(post["post_modified_gmt"].isoformat()))
        if post["post_name"]:
            f.write("slug: {}\n".format(post["post_name"]))

        post_data.execute("""
        SELECT wp_terms.term_id, slug FROM wp_term_relationships
        JOIN wp_term_taxonomy ON
          wp_term_taxonomy.term_taxonomy_id = wp_term_relationships.term_taxonomy_id AND
          object_id = {} AND
          taxonomy = 'category'
        JOIN wp_terms ON
        wp_term_taxonomy.term_id = wp_terms.term_id
        """.format(post["ID"]))
        categories = []
        for category in post_data:
            if post["language_code"] == "en":
                categories.append(category["slug"])
            else:
                post_data2.execute("""
                    SELECT slug FROM wp_icl_translations es
                    JOIN wp_icl_translations en ON
                      es.trid = en.trid AND
                      es.element_type = 'tax_category' AND
                      es.element_id = {} AND
                      en.language_code = 'en'
                    JOIN wp_terms ON
                      en.element_id = wp_terms.term_id
                """.format(category["term_id"]))
                tr_category = post_data2.fetchall()
                if tr_category:
                    categories.append(tr_category[0]["slug"])
                else:
                    categories.append(category["slug"])

        if categories:
            f.write("categories: [{}]\n".format(",".join(categories)))

        post_data.execute("""
        SELECT wp_terms.term_id, slug FROM wp_term_relationships
        JOIN wp_term_taxonomy ON
          wp_term_taxonomy.term_taxonomy_id = wp_term_relationships.term_taxonomy_id AND
          object_id = {} AND
          taxonomy = 'post_tag'
        JOIN wp_terms ON
        wp_term_taxonomy.term_id = wp_terms.term_id
        """.format(post["ID"]))
        tags = []
        for tag in post_data:
            if post["language_code"] == "en":
                tags.append(tag["slug"])
            else:
                post_data2.execute("""
                    SELECT slug FROM wp_icl_translations es
                    JOIN wp_icl_translations en ON
                      es.trid = en.trid AND
                      es.element_type = 'tax_post_tag' AND
                      es.element_id = {} AND
                      en.language_code = 'en'
                    JOIN wp_terms ON
                      en.element_id = wp_terms.term_id
                """.format(tag["term_id"]))
                tr_tag = post_data2.fetchall()
                if tr_tag:
                    tags.append(tr_tag[0]["slug"])
                else:
                    tags.append(tag["slug"])

        if tags:
            f.write("tags: [{}]\n".format(",".join(tags)))

        f.write("---\n")
        f.write(post["post_content"])

my.close()
