# -*- coding: utf-8 -*-
"""User and other DB models."""
import datetime as dt
from flask_security import UserMixin, RoleMixin
from beton.extensions import db
from beton.database import Column, Model, SurrogatePK, reference_col, relationship


class Role(SurrogatePK, Model):
    """A role for a user."""

    __tablename__ = 'roles'
    name = Column(db.String(80), unique=True, nullable=False)
    user_id = reference_col('users', nullable=True)
    user = relationship('User', backref='roles')
    description = Column(db.Text, nullable=True)

    def __init__(self, name, **kwargs):
        """Create instance."""
        db.Model.__init__(self, name=name, **kwargs)

    def __repr__(self):
        """Represent instance as a unique string."""
        return '<Role({name})>'.format(name=self.name)


class User(UserMixin, SurrogatePK, Model):
    """A user of the app."""

    __tablename__ = 'users'
    username = Column(db.String(80), unique=True, nullable=False)
    email = Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False, default='')
    active = Column(db.Boolean(), default=True)
    confirmed_at = Column(db.DateTime, nullable=True)

    def get_security_payload(self):
        '''Custom User Payload'''
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email
        }

    def __repr__(self):
        """Represent instance as a unique string."""
        return '<User({username!r})>'.format(username=self.username)


class Banner(SurrogatePK, Model):
    """Banner files."""

    __tablename__ = 'banners'
    filename = Column(db.String(191), unique=True, nullable=True)
    owner = Column(db.Integer(), unique=False, nullable=False)
    created_at = Column(db.DateTime, nullable=False, default=dt.datetime.utcnow)
    url = Column(db.String(2083), nullable=False)
    height = Column(db.Integer(), nullable=True)
    width = Column(db.Integer(), nullable=True)
    comments = Column(db.String(512), nullable=True)
    type = Column(db.String(21), unique=False, nullable=False)
    content = Column(db.String(256), unique=False, nullable=True)
    icon = Column(db.String(128), unique=False, nullable=True)
    bannerid = db.relationship("Campaignes", backref="banners")

    def __init__(self, filename, owner, created_at, url, height, width, comments, type, content, icon):
        """Create instance."""
        self.filename = filename
        self.owner = owner
        self.created_at = created_at
        self.url = url
        self.height = height
        self.width = width
        self.comments = comments
        self.type = type
        self.content = content
        self.icon = icon

    def __repr__(self):
        """Represent instance as a unique string."""
        return '<filename: {}, owner: {}, created_at: {}, url: {}, height: {}, \
width: {}, comment: {}, type: {}, content: {}, icon: {}>'.format(
            self.filename,
            self.owner,
            self.created_at,
            self.url,
            self.height,
            self.width,
            self.comments,
            self.type,
            self.content,
            self.icon
        )


class Zones(SurrogatePK, Model):
    """Zones.
    xy rectangle is constructed according to:
        https://svgwrite.readthedocs.io/en/master/classes/shapes.html#rect
    """

    __tablename__ = 'zones'
    websiteid = Column(db.Integer(), db.ForeignKey('websites.id', ondelete='CASCADE'), nullable=False)
    name = Column(db.String(100), unique=True, nullable=False)
    comments = Column(db.String(512), nullable=True)
    width = Column(db.Integer(), unique=False, nullable=False, default=0)
    height = Column(db.Integer(), unique=False, nullable=False, default=0)
    active = Column(db.Boolean(), default=True)
    x0 = Column(db.Integer(), unique=False, nullable=False, default=0)
    y0 = Column(db.Integer(), unique=False, nullable=False, default=0)
    x1 = Column(db.Integer(), unique=False, nullable=False, default=0)
    y1 = Column(db.Integer(), unique=False, nullable=False, default=0)
    zoneid = db.relationship("Campaignes", backref="zone")
    priceid = db.relationship("Prices", backref="zone")

    def __init__(self, websiteid, name, comments, width, height, active, x0, y0, x1, y1):
        """Create instance."""
        self.websiteid = websiteid
        self.name = name
        self.comments = comments
        self.width = width
        self.height = height
        self.active = active
        self.x0 = x0
        self.y0 = y0
        self.x1 = x1
        self.y1 = y1

    def __repr__(self):
        """Represent instance as a unique string."""
        return '<id: {}, name: {}, website: {}, comments: {}, active: {}, size: {}x{}, square: {}x{} {}x{}>'.format(
            self.id,
            self.name,
            self.website.name,  # foreign key
            self.comments,
            self.active,
            self.width,
            self.height,
            self.x0,
            self.y0,
            self.x1,
            self.y1
        )


o2c = db.Table('o2c',
               Column('order_id', db.Integer(), db.ForeignKey('orders.id'), primary_key=True),
               Column('campaign_id', db.Integer(), db.ForeignKey('campaignes.id'), primary_key=True)
               )


class Campaignes(SurrogatePK, Model):
    """Campaignes.
    Campaign will be uniquely identified by blake2b digest of name: blake2b(digest_size=6).hexdigest()
    """

    __tablename__ = 'campaignes'
    name = Column(db.String(100), unique=True, nullable=False)
    zoneid = Column(db.Integer(), db.ForeignKey('zones.id', ondelete='CASCADE'), nullable=False)
    ctype = Column(db.Integer(), unique=False, nullable=False)
    bannerid = Column(db.Integer(), db.ForeignKey('banners.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(db.DateTime, nullable=False, default=dt.datetime.utcnow)
    begins_at = Column(db.DateTime, nullable=False, default=dt.datetime.utcnow)
    stops_at = Column(db.DateTime, nullable=False, default=dt.datetime.utcnow)
    impressions = Column(db.Integer(), unique=False, nullable=True)
    comments = Column(db.Text, unique=False, nullable=False)
    active = Column(db.Boolean(), default=True)
    o2c = db.relationship('Orders', secondary=o2c, lazy='subquery',
                          backref=db.backref('campaigne', lazy='dynamic'))

    def __init__(self, name, zoneid, bannerid, ctype, created_at, begins_at,
                 stops_at, impressions, comments, active):
        """Create instance."""
        self.name = name
        self.zoneid = zoneid
        self.bannerid = bannerid
        self.ctype = ctype
        self.created_at = created_at
        self.begins_at = begins_at
        self.stops_at = stops_at
        self.impressions = impressions
        self.comments = comments
        self.active = active

    def __repr__(self):
        """Represent instance as a unique string."""
        return '<id: {}, name: {}, zoneid: {}, bannerid: {}, ctype: {}, created_at: {}, \
begins_at: {}, stops_at: {}, impressions: {}, comments: {}, active: {}>'.format(
            self.id,
            self.name,
            self.zoneid,
            self.bannerid,
            self.ctype,
            self.created_at,
            self.begins_at,
            self.stops_at,
            self.impressions,
            self.comments,
            self.active
        )


class Prices(SurrogatePK, Model):
    """Zone prices.
    """

    __tablename__ = 'zoneprice'
    zoneid = Column(db.Integer(), db.ForeignKey('zones.id', ondelete='CASCADE'), nullable=False)
    dayprice = Column(db.Integer(), unique=False, nullable=False, default=0)
    fiat = Column(db.String(3), unique=False, nullable=False)

    def __init__(self, zoneid, dayprice, fiat):
        """Create instance."""
        self.zoneid = zoneid
        self.dayprice = dayprice
        self.fiat = fiat

    def __repr__(self):
        """Represent instance as a unique string."""
        return '<zoneid: {}, dayprice: {}, fiat: {}>'.format(
            self.zoneid,
            self.dayprice,
            self.fiat
        )


class Orders(SurrogatePK, Model):
    """All orders"""

    __tablename__ = 'orders'
    user_id = Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    comments = Column(db.Text, unique=False, nullable=False)
    payment = db.relationship("Payments", backref="orders")
    o2c = db.relationship('Campaignes', secondary=o2c, lazy='subquery',
                          backref=db.backref('orders', lazy='dynamic'))

    def __init__(self, comments, user_id):
        """Create instance."""
        self.comments = comments
        self.user_id = user_id

    def __repr__(self):
        """Represent instance as a unique string."""
        return '<id: {}, comments: {}, user_id: {}>'.format(
            self.id,
            self.comments,
            self.user_id,
        )


class Payments(SurrogatePK, Model):
    """All payments"""

    __tablename__ = 'payments'
    order_id = Column(db.Integer(), db.ForeignKey('orders.id'), nullable=False)
    created_at = Column(db.DateTime, nullable=False, default=dt.datetime.utcnow)
    received_at = Column(db.DateTime, nullable=False)
    confirmed_at = Column(db.DateTime, nullable=False)
    btcpayserver_id = Column(db.String(22), nullable=False)
    posdata = Column(db.String(36), nullable=False)
    fiat = Column(db.String(3), unique=False, nullable=False)
    fiat_amount = Column(db.Numeric(16, 8), nullable=False)

    def __init__(self, fiat, fiat_amount, created_at, posdata,
                 received_at, confirmed_at, btcpayserver_id, order_id):
        """ Create instance."""
        self.fiat = fiat
        self.fiat_amount = fiat_amount
        self.created_at = created_at
        self.posdata = posdata
        self.received_at = received_at
        self.confirmed_at = confirmed_at
        self.btcpayserver_id = btcpayserver_id
        self.order_id = order_id

    def __repr__(self):
        """Represent instance as a unique string."""
        return '<id: {}, user_id: {}, fiat: {}, fiat_amount: {}, \
created_at: {}, order_id: {}, posdata: {} \
received_at: {}, confirmed_at: {}, btcpayserver_id: {}>'.format(
            self.id,
            self.orders.user_id,
            self.fiat,
            self.fiat_amount,
            self.created_at,
            self.order_id,
            self.posdata,
            self.received_at,
            self.confirmed_at,
            self.btcpayserver_id,
        )


class Websites(SurrogatePK, Model):
    """Websites"""

    __tablename__ = 'websites'
    name = Column(db.String(100), unique=True, nullable=False)
    comments = Column(db.Text, unique=False, nullable=False)
    active = Column(db.Boolean(), default=True)
    zones = db.relationship('Zones', backref='website')

    def __init__(self, name, comments, active):
        """Create instance."""
        self.name = name
        self.comments = comments
        self.active = active

    def __repr__(self):
        """Represent instance as a unique string."""
        return '<name: {}, comments: {}, active: {}>'.format(
            self.name,
            self.comments,
            self.active
        )


class Basket(SurrogatePK, Model):
    """User basket."""

    __tablename__ = 'basket'
    user_id = Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    campaigno = Column(db.Integer(), db.ForeignKey('campaignes.id', ondelete='CASCADE'), nullable=False)

    def __init__(self, user_id, campaigno):
        """Create instance."""
        self.user_id = user_id
        self.campaigno = campaigno

    def __repr__(self):
        """Represent instance as a unique string."""
        return '<user_id: {}, campaigno: {}>'.format(
            self.user_id,
            self.campaigno
        )


class Log(SurrogatePK, Model):
    """Operational logging."""

    __tablename__ = 'log'
    user_id = Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    datelog = Column(db.DateTime, nullable=False, default=dt.datetime.utcnow)
    logdata = Column(db.Text(), unique=False, nullable=False)

    def __init__(self, user_id, datelog, logdata):
        """Create instance."""
        self.user_id = user_id
        self.datelog = datelog
        self.logdata = logdata

    def __repr__(self):
        """Represent instance as a unique string."""
        return '<user_id: {}, logdata: {}, datelog: {}>'.format(
            self.user_id,
            self.logdata,
            self.datelog
        )


class Impressions(SurrogatePK, Model):
    """Impressions data stats"""

    __tablename__ = 'impressions'
    cid = Column(db.Integer(), db.ForeignKey('campaignes.id', ondelete='CASCADE'), nullable=False)
    impressions = Column(db.Integer(), unique=False, nullable=True)
    path = Column(db.String(250), unique=True, nullable=False)

    def __init__(self, cid, impressions, path):
        """Create instance."""
        self.cid = cid
        self.impressions = impressions
        self.path = path

    def __repr__(self):
        """Represent instance as a unique string."""
        return '<cid: {}, impressions: {}, path: {}>'.format(
            self.cid,
            self.impressions,
            self.path
        )
