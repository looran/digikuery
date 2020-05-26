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
    DIGIKAM_INTERNAL_TAGS_ROOT = ['_Digikam_Internal_Tags_']
    DIGIKAM_BLACKLIST_TAGS = [ "Color Label None", "Pick Label None", "Current Version" ]
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

    def query_album(self, name):
        s = ""
        if name == '.*':
            name = None
        for album, tags in sorted(self._query_albums(name).items()):
            s += "{} ({})\n".format(album, len(tags))
            s += "    {}\n".format(' '.join([ "{} ({})".format(t, c) for t, c in sorted(tags.items(), key=lambda i: i[1], reverse=True) ]))
        return s

    def query_tag(self, expr=None, sort_count=False):
        s = ""
        # go over precomputed tags list and match regex
        # we use precomputed tags from self._tagstree_to_list so we can match 'expr' against
        # aggregated tag name from the tree instead of single tag name
        tags = dict()
        for tag, tagname in self._tagstree_to_list():
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
                        s += "            {}\n".format(i.name)
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

    def _query_albums(self, names=None):
        """ names: None for all albums, string for 'like' match, list for exact album names
            returns { 'albumname': { 'tagname': tagcount } } """
        albums = defaultdict(dict)
        query = self.session.query(Album, Tag, sqlalchemy.func.count(Tag.name)).join(imagetag).join(Image).join(Album)
        if type(names) is list:
            query = query.filter(Album.relativePath.in_(names))
        elif type(names) is str:
            query = query.filter(Album.relativePath.like('%'+names+'%'))
        for res in query.group_by(Album).group_by(Tag):
            if res[1].name in Tag.DIGIKAM_BLACKLIST_TAGS:
                continue
            albums[res[0].relativePath][res[1].name] = res[2]
        return albums

    def _tagstree_to_list(self):
        """ query digikam tags tree and constuct all tags full name """
        def _getchilds(tag, name=""):
            if tag.name in Tag.DIGIKAM_INTERNAL_TAGS_ROOT:
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

    def _tag_fullname(self, tag):
        """ returns string of tag full name
            @tag: child tag object """
        if len(tag.parent):
            return self._tag_fullname(tag.parent[0]) + '/' + tag.name
        else:
            return tag.name

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Digikam database query tool')
    parser.add_argument('-a', '--album', nargs='?', const=".*", help='query album tags')
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
    elif args.album:
        print(dk.query_album(args.album))
    elif args.tag:
        print(dk.query_tag(args.tag, args.count))
    else:
        print(dk.stats())
