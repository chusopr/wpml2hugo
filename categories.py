#!/usr/bin/env python3
import mysql.connector
import getpass
from sys import argv, stderr

# See the comments in tag.py because this is basically the same

if len(argv) != 4:
    print("Syntax: {} <hostname> <database> <user>".format(argv[0]), file=stderr)
    exit(1)

password = getpass.getpass("Password for MySQL user {} at MySQL server {} and database {}: ".format(argv[3], argv[1], argv[2]))

my = mysql.connector.connect(user=argv[3], password=password, host=argv[1], database=argv[2])

categories = my.cursor(dictionary=True)

categories.execute("""
SELECT
  wp_terms_en.slug AS slug_en,
  wp_terms_en.name AS name_en,
  wp_terms_es.slug AS slug_es,
  wp_terms_es.name as name_es
FROM wp_terms wp_terms_en
JOIN wp_icl_translations wp_icl_translations_en
ON wp_terms_en.term_id = wp_icl_translations_en.element_id AND wp_icl_translations_en.language_code = 'en'
LEFT JOIN wp_icl_translations wp_icl_translations_es
ON wp_icl_translations_es.trid = wp_icl_translations_en.trid AND wp_icl_translations_es.language_code = 'es'
JOIN wp_terms wp_terms_es ON wp_terms_es.term_id = wp_icl_translations_es.element_id
WHERE
  'tax_category' IN (wp_icl_translations_es.element_type, wp_icl_translations_en.element_type)
UNION
SELECT
  wp_terms_en.slug AS slug_en,
  wp_terms_en.name AS name_en,
  wp_terms_es.slug AS slug_es,
  wp_terms_es.name as name_es
FROM wp_terms wp_terms_en
JOIN wp_icl_translations wp_icl_translations_en
ON wp_terms_en.term_id = wp_icl_translations_en.element_id AND wp_icl_translations_en.language_code = 'en'
RIGHT JOIN wp_icl_translations wp_icl_translations_es
ON wp_icl_translations_es.trid = wp_icl_translations_en.trid
JOIN wp_terms wp_terms_es ON wp_terms_es.term_id = wp_icl_translations_es.element_id
WHERE
  wp_icl_translations_en.trid IS NULL AND
  'tax_category' IN (wp_icl_translations_es.element_type, wp_icl_translations_en.element_type)
UNION
SELECT
  wp_terms_en.slug AS slug_en,
  wp_terms_en.name AS name_en,
  wp_terms_es.slug AS slug_es,
  wp_terms_es.name as name_es
FROM wp_terms wp_terms_es
JOIN wp_icl_translations wp_icl_translations_es
ON wp_terms_es.term_id = wp_icl_translations_es.element_id AND wp_icl_translations_es.language_code = 'es'
RIGHT JOIN wp_icl_translations wp_icl_translations_en
ON wp_icl_translations_en.trid = wp_icl_translations_es.trid
JOIN wp_terms wp_terms_en ON wp_terms_en.term_id = wp_icl_translations_en.element_id
WHERE
  wp_icl_translations_es.trid IS NULL AND
  'tax_category' IN (wp_icl_translations_en.element_type, wp_icl_translations_es.element_type);
""")

for category in categories:
    if category["slug_en"] is not None:
        with open("categories/{}.en.md".format(category["slug_en"] if category["name_es"] != category["name_en"] else category["slug_es"]), "w") as f:
            f.write("""---
layout: category
title: {1}
pagecat: {0}
url: /{0}/
---""".format(category["slug_en"], category["name_en"]))
    if category["slug_es"] is not None:
        with open("categories/{}.es.md".format(category["slug_en"] if category["slug_en"] is not None and category["name_es"] != category["name_en"] else category["slug_es"]), "w") as f:
            f.write("""---
layout: category
title: {1}
pagecat: {2}
url: /{0}/
---""".format(category["slug_es"], category["name_es"], category["slug_en"] if category["slug_en"] is not None else category["slug_es"]))
    if category["name_es"] == category["name_en"]:
        print("Redirect category: {}, {}".format(category["slug_es"], category["slug_en"]))

my.close()
