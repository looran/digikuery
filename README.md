digikuery is a script to perform queries in [digikam](https://www.digikam.org/) photo manager database, to fetch photo tags for example.

## Usage

``` bash
usage: digikuery [-h] [-d DBPATH] [-i] [-r ROOT] [-s] [-t [TAG]] [-v]

Digikam database query tool

optional arguments:
  -h, --help            show this help message and exit
  -d DBPATH, --dbpath DBPATH
                        database path
  -i, --interactive     interactive shell mode
  -r ROOT, --root ROOT  restrict query to this root album
  -s, --schema          dump schema
  -t [TAG], --tag [TAG]
                        query tags
  -v, --verbose         show more details
```

## Example: Query which albums contain given tag expression

Bellow we look for the "semaphore" name in all tags.

The query returns 2 tags "TagCommunication/Semaphore/Bleu" and "TagAlphabet/Semaphore", listing for each tag the albums containing tagged pictures.

Providing -v option would list the picture names too.

``` bash
$ digikuery -t semaphore
  3 TagCommunication/Semaphore/Bleu
      3 ablum_france
      2 album_grece
      2 album_albanie
  1 TagAlphabet/Semaphore
      19 album_photos_19e_siecle
```

## Install

$ sudo make install

