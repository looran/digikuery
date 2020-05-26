#!/usr/bin/env python3

# digikam database query tool
# 2020, Laurent Ghigonis <ooookiwi@gmail.com>

# external ressources for digikam sqlite or sqlalchemy
# * 2020 digikam+sqlite https://github.com/clutterstack/digikam-to-tiddlywiki/blob/master/Digikam%20to%20TiddlyWiki.ipynb
# * 2019 digikam+sqlite https://github.com/ksmathers/digikam-migrate/blob/master/migrate_thumbnails.py
# * 2018 digikam+sqlite https://github.com/lsaffre/picsel/blob/master/digikam2blog.py
# * 2008 digikam+sqlalchemy http://blog.mekk.waw.pl/archives/12-Moving-images-from-F-Spot-to-digiKam.html

import re
import argparse
import pathlib
from collections import defaultdict
import sqlalchemy
from sqlalchemy import Column, Table, DateTime, UnicodeText, Integer, String, Unicode, ForeignKey, MetaData
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

imagetag = Table('ImageTags', Base.metadata,
        Column('imageid', ForeignKey('Images.id'), primary_key=True),
        Column('tagid', ForeignKey('Tags.id'), primary_key=True)
)

class Image(Base):
    __tablename__ = "Images"
    id = Column(Integer, primary_key=True)
    album_id = Column("album", Integer, ForeignKey('Albums.id'))
    album = relationship("Album", back_populates="images")
    name = Column(Unicode())
    tags = relationship("Tag", secondary=imagetag, back_populates="images")
 
class Album(Base):
    __tablename__ = "Albums"
    id = Column(Integer, primary_key=True)
    relativePath = Column(Unicode(), unique=True)
    albumRoot_id = Column("albumRoot", Unicode(), ForeignKey('AlbumRoots.id'))
    albumRoot = relationship("AlbumRoot", back_populates="albums")
    images = relationship("Image", back_populates="album")

class AlbumRoot(Base):
    __tablename__ = "AlbumRoots"
    id = Column(Integer, primary_key=True)
    label = Column(Unicode())
    albums = relationship("Album", back_populates="albumRoot")

class Tag(Base):
    __tablename__ = "Tags"
    id = Column(Integer, ForeignKey('Tags.pid'), primary_key=True)
    pid = Column(Integer, ForeignKey('Tags.id'))
    parent = relationship("Tag", foreign_keys='Tag.id')
    name = Column(Unicode(), unique=True)
    images = relationship("Image", secondary=imagetag, back_populates="tags")
    childs = relationship("Tag", foreign_keys='Tag.pid')

class Digikuery(object):
    def __init__(self, dbpath, rootalbum, verbose):
        self.dbpath = dbpath
        self.rootalbum = rootalbum
        self.verbose = verbose
        self.engine = sqlalchemy.create_engine(dbpath, echo=False)
        Session = sqlalchemy.orm.sessionmaker()
        Session.configure(bind=self.engine)
        self.session = Session()
        self.metadata = MetaData()
        self.metadata.reflect(self.engine)
        self.tags = self._tagstree_to_list()

    def query_tag(self, expr=None, sort_count=False):
        s = ""
        # go over precomputed tags list and match regex
        tags = dict()
        for tag, tagname in self.tags:
                if expr and not re.match(r".*%s.*" % expr, tagname, re.IGNORECASE):
                    continue
                images = defaultdict(list)
                for i in tag.images:
                    if i.album:
                        if self.rootalbum:
                            if i.album.albumRoot.label != self.rootalbum:
                                continue
                            album = i.album.relativePath[1:]
                        else:
                            album = "%s%s" % (i.album.albumRoot.label, i.album.relativePath)
                    else:
                        album = "no-album"
                    images[album].append(i)
                # sort albums by images count
                albums = sorted(images.items(), key=lambda k_v: k_v[0])
                if sort_count:
                    albums = sorted(albums, key=lambda k_v: len(k_v[1]), reverse=True)
                if len(albums) > 0:
                    tags[tagname] = { 'tag': tag, 'albums': albums }
        # display tags sorted by albums count
        for tagname, tag in sorted(tags.items(), key=lambda k_v: len(k_v[1]['albums']), reverse=True):
            s += "{:3} {}\n".format(len(tag['albums']), tagname)
            for album in tag['albums']:
                s += "    {:3} {}\n".format(len(album[1]) if sort_count else "", album[0])
                if self.verbose:
                    for i in album[1]:
                        s += "        {}\n".format(i.name)
        return s

    def schema(self):
        s = "database shema :"
        for k, v in self.metadata.tables.items():
            s += "\n- %s\n" % k
            s += '\n'.join(['%s.%s %s' % (k, c, t.type) for c, t in v.columns.items()])
        return s

    def stats(self):
        if self.dbpath.startswith("sqlite://"):
            dbsize = "%.2fMB" % (pathlib.Path(self.dbpath[10:]).stat().st_size / 1000000)
        else:
            dbsize = "N/A"
        albums_count = self.session.query(Album).count()
        images_count = self.session.query(Image).count()
        tags_count = self.session.query(Tag).count()
        return """database {dbpath}
    size {dbsize}
  albums {albums_count}
  images {images_count}
    tags {tags_count}""".format(dbpath=self.dbpath, dbsize=dbsize, albums_count=albums_count, images_count=images_count, tags_count=tags_count)

    def _tagstree_to_list(self):
        """ query digikam tags tree and constuct all tags full name """
        def _getchilds(tag, name=""):
            if tag.name == '_Digikam_Internal_Tags_':
                return list()
            name = (name + '/' if tag.pid != 0 else "") + tag.name
            res = [ (tag, name) ]
            for child in tag.childs:
                res.extend(_getchilds(child, name))
            return res
        l = list()
        for roottag in self.session.query(Tag).filter_by(pid=0).all():
            l.extend(_getchilds(roottag))
        return l

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Digikam database query tool')
    parser.add_argument('-c', '--count', action='store_true', help='sort by result count')
    parser.add_argument('-d', '--dbpath', help='database path', default="sqlite:///{home}/Pictures/digikam4.db".format(home=str(pathlib.Path.home())))
    parser.add_argument('-i', '--interactive', action='store_true', help='interactive shell mode')
    parser.add_argument('-r', '--root', help='restrict query to this root album')
    parser.add_argument('-s', '--schema', action='store_true', help='dump schema')
    parser.add_argument('-t', '--tag', nargs='?', const='.*', help='query tags')
    parser.add_argument('-v', '--verbose', action='store_true', help='show more details')
    args = parser.parse_args()
    dk = Digikuery(args.dbpath, args.root, args.verbose)
    if args.interactive:
        print("""Interactive mode
available objects:
   dk.engine
   dk.session
   dk.metadata
   dk.tags
available functions:
   dk.query_tag(tag)
   dk.schema()
   dk.stats()

running ipython...""")
        from IPython import embed
        embed()
    elif args.schema:
        print(dk.schema())
    elif args.tag:
        print(dk.query_tag(args.tag, args.count))
    else:
        print(dk.stats())
