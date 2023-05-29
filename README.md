digikuery is a script to perform queries in [digikam](https://www.digikam.org/) (photo manager) database.

It can
* Query albums which contains tags matching a given regex
* Query most used tags and corresponding albums
* Print other tags present in matching albums
* List digikam database structure
* Provide an interactive python shell for manual queries

## Usage

``` bash
usage: digikuery.py [-h] [-d DBPATH] [-F] [-R ROOT] [-T [FILTER_TAGS]] {shell,schema,album,tag,stats} ...

digikuery - Digikam database query tool - v20230529

positional arguments:
  {shell,schema,album,tag,stats}
    shell                       spawn ipython shell to explor digikam database
    schema                      dump digikam database schema
    album               [album] list tags for one or all albums
    tag                 [tag]   list all tags or query single tag
                        -C      sort by result count
                        -I      show image details
    stats                       show digikam database statistics (default)

options:
  -h, --help            show this help message and exit
  -d DBPATH, --dbpath DBPATH
                        database path
  -F, --full-tagname    display full tag name
  -R ROOT, --root ROOT  restrict query to this root album
  -T [FILTER_TAGS], --filter-tags [FILTER_TAGS]
                        show and filter tags for displayed albums

examples:
List albums when tag 'Paquerette' is present, together with other tags of this album
$ digikuery tag Paquerette
```

## Install

``` bash
$ pip install digikuery
```

## Example: Query which albums contain given tag expression

Bellow we look for the "semaphore" name in all tags.

The query returns 2 tags "TagCommunication/Semaphore/Bleu" and "TagAlphabet/Semaphore", listing for each tag the albums containing tagged pictures.

``` bash
$ digikuery tag semaphore
  3 TagCommunication/Semaphore/Bleu
      album_albanie
      album_france
      album_grece
  1 TagAlphabet/Semaphore
      album_photos_19e_siecle
```

Providing -I option would list the picture names.

Let's just sort them by picture count:

```
$ digikuery tag -C semaphore
  3 TagCommunication/Semaphore/Bleu
      3 album_france
      2 album_grece
      2 album_albanie
  1 TagAlphabet/Semaphore
      19 album_photos_19e_siecle
```

For each matching album we can show if it contains other tags, for example tags maching "access"

``` bash
$ digikuery -T access tag semaphore
  3 TagCommunication/Semaphore/Bleu
      album_france
        TagAccess/Walking (9), TagAccess/Train(1)
      album_grece
		TagAccess/Car(6), TagAccess/Walking (3)
      album_albanie
		TagAccess/Walking (5)
```

## Internals

digikuery uses sqlalchemy to map digikam database to python objects.
