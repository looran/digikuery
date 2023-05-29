#!/usr/bin/env python3

# Digikam database query tool
# 2020, 2021, 2023 Laurent Ghigonis <ooookiwi@gmail.com>

# external ressources for digikam sqlite or sqlalchemy
# * 2020 digikam+sqlite https://github.com/clutterstack/digikam-to-tiddlywiki/blob/master/Digikam%20to%20TiddlyWiki.ipynb
# * 2019 digikam+sqlite https://github.com/ksmathers/digikam-migrate/blob/master/migrate_thumbnails.py
# * 2018 digikam+sqlite https://github.com/lsaffre/picsel/blob/master/digikam2blog.py
# * 2008 digikam+sqlalchemy http://blog.mekk.waw.pl/archives/12-Moving-images-from-F-Spot-to-digiKam.html

VERSION = "20230529"
DESCRIPTION = 'Digikam database query tool'
EXAMPLES = """examples:
List albums when tag 'Paquerette' is present, together with other tags of this album
$ digikuery tag Paquerette
"""

import re
import sys
import argparse
import pathlib
from collections import defaultdict

import sqlalchemy
from sqlalchemy import Column, Table, DateTime, UnicodeText, Integer, String, Unicode, ForeignKey, MetaData
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

imagetag = Table('ImageTags', Base.metadata,
        Column('imageid', ForeignKey('Images.id'), primary_key=True),
        Column('tagid', ForeignKey('Tags.id'), primary_key=True)
)

def help():
    print("""Interactive mode help:
   available objects
      dk.engine
      dk.session
      dk.metadata
   available functions
      help()
         print this message
      dk.query_album(album)
      dk.query_tag(tag)
      dk.schema()
      dk.stats()""")

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
    DIGIKAM_BLACKLIST_TAGS = [ "Color Label None", "Pick Label None", "Current Version", "Original Version", "Intermediate Version", "Scanned for Faces" ]
    __tablename__ = "Tags"
    id = Column(Integer, ForeignKey('Tags.pid'), primary_key=True)
    pid = Column(Integer, ForeignKey('Tags.id'))
    parent = relationship("Tag", foreign_keys='Tag.id')
    name = Column(Unicode(), unique=True)
    images = relationship("Image", secondary=imagetag, back_populates="tags")
    childs = relationship("Tag", foreign_keys='Tag.pid')

class Digikuery(object):
    def __init__(self, dbpath, root, filter_tags, full_tagname):
        self.dbpath = dbpath
        self.root = root
        self.filter_tags = filter_tags
        self.full_tagname = full_tagname
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
            s += "{} ({})\n".format(album[1:], len(tags))
            s += "    {}\n".format(' '.join([ "{} ({})".format(t, c) for t, c in sorted(tags.items(), key=lambda i: i[1], reverse=True) ]))
        return s

    def query_tag(self, expr=None, show_image=False, sort_count=False):
        s = ""
        # go over precomputed tags list and match regex
        # we use precomputed tags from self._tagstree_to_list so we can match 'expr' against
        # aggregated tag name from the tree instead of single tag name
        tags = dict()
        for tag, tagname in self._tagstree_to_list():
                if expr and not re.match(r".*%s.*" % expr, tagname, re.IGNORECASE):
                    continue
                results = defaultdict(list)
                for i in tag.images:
                    if i.album:
                        if i.album.albumRoot:
                            if self.root:
                                if i.album.albumRoot.label != self.root:
                                    continue
                            results[(i.album.albumRoot.label, i.album.relativePath)].append(i)
                        else:
                            print("warning: tag %s image %s album %s (%s) has no albumRoot" % (tagname, i.name, i.album.relativePath, i.album_id))
                    else:
                        print("warning: tag %s image %s has no album" % (tagname, i.name))
                # sort albums by name
                albums = sorted(results.items(), key=lambda k_v: k_v[0])
                if sort_count:
                    # sort albums by images count
                    albums = sorted(albums, key=lambda k_v: len(k_v[1]), reverse=True)
                if len(albums) > 0:
                    tags[tagname] = { 'tag': tag, 'albums': albums }
        # display tags sorted by albums count
        for tagname, tag in sorted(tags.items(), key=lambda k_v: len(k_v[1]['albums']), reverse=True):
            s += "{:3} {}\n".format(len(tag['albums']), tagname)
            if self.filter_tags is not None:
                filter_tags = self._query_albums([ album[0][1] for album in tag['albums'] ], skiptag=tagname)
            for album in tag['albums']:
                if self.root:
                    albumname = album[0][1][1:] # remove heading '/'
                else:
                    albumname = "%s %s" % (album[0][0], album[0][1][1:])
                s += "    {:3} {}\n".format(len(album[1]) if sort_count else "", albumname)
                if self.filter_tags is not None and len(filter_tags[album[0][1]]) > 0:
                    if self.full_tagname:
                        s += "%s\n" % '\n'.join([ "         {:3} {}".format(c, t) for t, c in sorted(filter_tags[album[0][1]].items(), key=lambda i: i[1], reverse=True) ])
                    else:
                        s += "            {}\n".format(' '.join([ "{} ({})".format(t, c) for t, c in sorted(filter_tags[album[0][1]].items(), key=lambda i: i[1], reverse=True) ]))
                if show_image:
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

    def _query_albums(self, names=None, skiptag=None):
        #print("XXX _query_albums self.filter_tags=%s" % self.filter_tags)
        """ names: None for all albums, string for 'like' match, list for exact album names
            skiptag: tag name to skip
            returns { 'albumname': { 'tagname': tagcount } } """
        albums = defaultdict(dict)
        query = self.session.query(Album, Tag, sqlalchemy.func.count(Tag.name)).join(imagetag).join(Image).join(Album)
        if self.root:
            query = query.join(AlbumRoot)
            query = query.filter(AlbumRoot.label == self.root)
        if type(names) is list:
            query = query.filter(Album.relativePath.in_(names))
        elif type(names) is str:
            query = query.filter(Album.relativePath.like('%'+names+'%'))
        for res in query.group_by(Album).group_by(Tag):
            if res[1].name in Tag.DIGIKAM_BLACKLIST_TAGS:
                continue
            tag_fullname = self._tag_fullname(res[1])
            if skiptag and (skiptag == res[1].name or skiptag == tag_fullname):
                continue
            #print("XXX _query_albums res %s # %s # %s # %s" % (type(names), names, tag_fullname, self.filter_tags))
            if type(names) is list and self.filter_tags != '.*' and not re.match(r".*%s.*" % self.filter_tags, tag_fullname, re.IGNORECASE):
                continue
            if self.full_tagname:
                albums[res[0].relativePath][tag_fullname] = res[2]
            else:
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

def main():
    parser = argparse.ArgumentParser(description="digikuery - "+DESCRIPTION+" - v"+VERSION, epilog=EXAMPLES, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-d', '--dbpath', help='database path', default="sqlite:///{home}/Pictures/digikam4.db".format(home=str(pathlib.Path.home())))
    parser.add_argument('-F', '--full-tagname', action='store_true', help='display full tag name')
    parser.add_argument('-R', '--root', help='restrict query to this root album')
    parser.add_argument('-T', '--filter-tags', nargs='?', default='.*', help='show and filter tags for displayed albums')
    subparsers = parser.add_subparsers(dest='action')

    parse_sub = subparsers.add_parser('shell',  help='        spawn ipython shell to explor digikam database')

    parse_sub = subparsers.add_parser('schema', help='        dump digikam database schema')

    parse_sub = subparsers.add_parser('album',  help='[album] list tags for one or all albums')
    parse_sub.add_argument('album_name', nargs='?', const=".*")

    parse_sub2 = subparsers.add_parser('tag',   help='[tag]   list all tags or query single tag\n-C      sort by result count\n-I      show image details')
    parse_sub2.add_argument('tag_name', nargs='?', const='.*')
    parse_sub2.add_argument('-C', '--sort-count', action='store_true')
    parse_sub2.add_argument('-I', '--show-image', action='store_true')

    parse_sub = subparsers.add_parser('stats',  help='        show digikam database statistics (default)')

    args = parser.parse_args()

    dk = Digikuery(args.dbpath, args.root, args.filter_tags, args.full_tagname)
    if args.action == 'shell':
        help()
        print("running ipython...")
        from IPython import embed
        embed()
    elif args.action == 'schema':
        print(dk.schema())
    elif args.action == 'album':
        print(dk.query_album(args.album_name))
    elif args.action == 'tag':
        print(dk.query_tag(args.tag_name, args.show_image, args.sort_count))
    else:
        print(dk.stats())

if __name__ == "__main__":
    sys.exit(main())
