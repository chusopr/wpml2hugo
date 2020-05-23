#!/usr/bin/env python3
import mysql.connector
import getpass
from sys import argv, stderr

if len(argv) != 4:
    print("Syntax: {} <hostname> <database> <user>".format(argv[0]), file=stderr)
    exit(1)

password = getpass.getpass("Password for MySQL user {} at MySQL server {} and database {}: ".format(argv[3], argv[1], argv[2]))

my = mysql.connector.connect(user=argv[3], password=password, host=argv[1], database=argv[2])

tags = my.cursor(dictionary=True)

# Getting the list of tags would be as simple as:
# tags.execute("SELECT wp_terms.term_id, slug, name FROM wp_terms JOIN wp_term_taxonomy ON wp_terms.term_id=wp_term_taxonomy.term_id WHERE wp_term_taxonomy.taxonomy = 'post_tag' AND wp_term_taxonomy.count > 0")
# But since I use WPML and also because MySQL doesn't support OUTER JOIN, it's much more complex:

tags.execute("""
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
  'tax_post_tag' IN (wp_icl_translations_es.element_type, wp_icl_translations_en.element_type)
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
  'tax_post_tag' IN (wp_icl_translations_es.element_type, wp_icl_translations_en.element_type)
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
  'tax_post_tag' IN (wp_icl_translations_en.element_type, wp_icl_translations_es.element_type);
""")

for tag in tags:
    if tag["slug_en"] is not None:
        with open("tags/{}.en.md".format(tag["slug_en"] if tag["name_es"] != tag["name_en"] else tag["slug_es"]), "w") as f:
            f.write("""---
layout: tag
title: {1}
pagetag: {0}
url: /tag/{0}/
---""".format(tag["slug_en"], tag["name_en"]))
    if tag["slug_es"] is not None:
        # To let Hugo know when tags are translated, we use the same filename for both languages if possible
        # Also, when they have the same name but different slug, I keep the Spanish one because I had used <slug>-en for English ones
        with open("tags/{}.es.md".format(tag["slug_en"] if tag["slug_en"] is not None and tag["name_es"] != tag["name_en"] else tag["slug_es"]), "w") as f:
            f.write("""---
layout: tag
title: {1}
pagetag: {0}
url: /tag/{0}/
---""".format(tag["slug_es"], tag["name_es"]))
    if tag["name_es"] == tag["name_en"]:
        # If the tag has the same name in both languages, Hugo supports using the same slug, but WordPress doesn't
        # We print those cases to stdout to manually create the redirect from the old URLs to the new ones
        print("Redirect tag: {}, {}".format(tag["slug_es"], tag["slug_en"]))

my.close()
