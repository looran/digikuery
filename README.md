digikuery is a script to perform queries in [digikam](https://www.digikam.org/) photo manager database.

It can
* Query albums which contains tags matching a given regex
* Query most used tags and corresponding albums
* Print other tags present in matching albums
* List digikam database structure
* Provide an interactive python shell for manual queries

## Usage

``` bash
usage: digikuery [-h] [-a [ALBUM]] [-d DBPATH] [-i] [-s] [-t [TAG]] [-C] [-F]
                 [-I] [-R ROOT] [-T [ALBUM_TAGS]]

Digikam database query tool

optional arguments:
  -h, --help            show this help message and exit
  -a [ALBUM], --album [ALBUM]
                        query album tags
  -d DBPATH, --dbpath DBPATH
                        database path
  -i, --interactive     interactive shell mode
  -s, --schema          dump schema
  -t [TAG], --tag [TAG]
                        query tags
  -C, --sort-count      sort by result count
  -F, --full-tagname    display full tag name
  -I, --show-image      show image details
  -R ROOT, --root ROOT  restrict query to this root album
  -T [ALBUM_TAGS], --album-tags [ALBUM_TAGS]
                        show and filter tags for displayed albums
```

## Example: Query which albums contain given tag expression

Bellow we look for the "semaphore" name in all tags.

The query returns 2 tags "TagCommunication/Semaphore/Bleu" and "TagAlphabet/Semaphore", listing for each tag the albums containing tagged pictures.

``` bash
$ digikuery -t semaphore
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
$ digikuery -t semaphore -C
  3 TagCommunication/Semaphore/Bleu
      3 album_france
      2 album_grece
      2 album_albanie
  1 TagAlphabet/Semaphore
      19 album_photos_19e_siecle
```

For each matching album we can show if it contains other tags, for example tags maching "access"

``` bash
$ digikuery -t semaphore -T access
  3 TagCommunication/Semaphore/Bleu
      album_france
        TagAccess/Walking (9), TagAccess/Train(1)
      album_grece
		TagAccess/Car(6), TagAccess/Walking (3)
      album_albanie
		TagAccess/Walking (5)
```

## Install

``` bash
$ sudo make install
```

## Internals

digikuery uses sqlalchemy to map digikam database to python objects.
