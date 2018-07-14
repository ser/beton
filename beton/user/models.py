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
    filename = Column(db.String(191), unique=True, nullable=False)
    owner = Column(db.Integer(), unique=False, nullable=False)
    created_at = Column(db.DateTime, nullable=False, default=dt.datetime.utcnow)
    url = Column(db.String(2083), nullable=False)
    height = Column(db.Integer(), nullable=False)
    width = Column(db.Integer(), nullable=False)
    comments = Column(db.String(512), nullable=True)
    bannerid = db.relationship("Orders")

    def __init__(self, filename, owner, created_at, url, height, width, comments):
        """Create instance."""
        self.filename = filename
        self.owner = owner
        self.created_at = created_at
        self.url = url
        self.height = height
        self.width = width
        self.comments = comments

    def __repr__(self):
        """Represent instance as a unique string."""
        return '<filename: {}, owner: {}, created_at: {}, url: {}, height: {}, \
width: {}, comment: {}>'.format(
            self.filename,
            self.owner,
            self.created_at,
            self.url,
            self.height,
            self.width,
            self.comments
        )


class Prices(SurrogatePK, Model):
    """Zone prices.
    Rectangle is constructed according to:
        https://svgwrite.readthedocs.io/en/master/classes/shapes.html#rect
    """

    __tablename__ = 'zoneprice'
    zoneid = Column(db.Integer(), unique=True, nullable=False)
    dayprice = Column(db.Integer(), unique=False, nullable=False, default=0)
    x0 = Column(db.Integer(), unique=False, nullable=False, default=0)
    y0 = Column(db.Integer(), unique=False, nullable=False, default=0)
    x1 = Column(db.Integer(), unique=False, nullable=False, default=0)
    y1 = Column(db.Integer(), unique=False, nullable=False, default=0)

    def __init__(self, zoneid, dayprice, x0, y0, x1, y1):
        """Create instance."""
        self.zoneid = zoneid
        self.dayprice = dayprice
        self.x0 = x0
        self.y0 = y0
        self.x1 = x1
        self.y1 = y1

    def __repr__(self):
        """Represent instance as a unique string."""
        return '<zoneid: {}, dayprice: {}, \
square: {}x{} {}x{}>'.format(
            self.zoneid,
            self.dayprice,
            self.x0,
            self.y0,
            self.x1,
            self.y1
        )


class Orders(SurrogatePK, Model):
    """All orders"""

    __tablename__ = 'orders'
    campaigno = Column(db.Integer(), unique=True, nullable=False)
    zoneid = Column(db.Integer(), db.ForeignKey('zoneprice.zoneid'), nullable=False)
    created_at = Column(db.DateTime, nullable=False, default=dt.datetime.utcnow)
    begins_at = Column(db.DateTime, nullable=False, default=dt.datetime.utcnow)
    stops_at = Column(db.DateTime, nullable=False, default=dt.datetime.utcnow)
    paymentno = Column(db.Integer(), unique=False, nullable=True)
    bannerid = Column(db.Integer(), db.ForeignKey('banners.id'), nullable=False)
    name = Column(db.Text, unique=False, nullable=False)
    comments = Column(db.Text, unique=False, nullable=False)
    impressions = Column(db.Integer(), unique=False, nullable=True)
    user_id = Column(db.Integer(), db.ForeignKey('users.id'), nullable=False)

    def __init__(self, campaigno, zoneid, created_at, begins_at,
                 stops_at, paymentno, bannerid, name, comments,
                 impressions, user_id):
        """Create instance."""
        self.campaigno = campaigno
        self.zoneid = zoneid
        self.created_at = created_at
        self.begins_at = begins_at
        self.stops_at = stops_at
        self.paymentno = paymentno
        self.bannerid = bannerid
        self.name = name
        self.comments = comments
        self.impressions = impressions
        self.user_id = user_id

    def __repr__(self):
        """Represent instance as a unique string."""
        return '<campaigno: {}, zoneid: {}, created_at: {}, \
begins_at: {}, stops_at: {}, name: {}, comments: {}, \
paymentno: {}, bannerid: {}, impressions: {}, user_id: {}>'.format(
            self.campaigno,
            self.zoneid,
            self.created_at,
            self.begins_at,
            self.stops_at,
            self.name,
            self.comments,
            self.paymentno,
            self.bannerid,
            self.impressions,
            self.user_id
        )


class Payments(SurrogatePK, Model):
    """All payments"""

    __tablename__ = 'payments'
    blockchain = Column(db.String(10), unique=False, nullable=False)
    address = Column(db.String(64), unique=True, nullable=False)
    total_coins = Column(db.Numeric(16, 8))
    txno = Column(db.String(64), unique=False, nullable=True)
    created_at = Column(db.DateTime, nullable=False, default=dt.datetime.utcnow)
    received_at = Column(db.DateTime, nullable=False)
    confirmed_at = Column(db.DateTime, nullable=False)
    bip70_id = Column(db.String(10), nullable=False)
    user_id = Column(db.Integer(), db.ForeignKey('users.id'), nullable=False)

    def __init__(self, blockchain, address, txno, total_coins, created_at,
                 received_at, confirmed_at, bip70_id, user_id):
        """ Create instance."""
        self.blockchain = blockchain
        self.address = address
        self.txno = txno
        self.total_coins = total_coins
        self.created_at = created_at
        self.received_at = received_at
        self.confirmed_at = confirmed_at
        self.bip70_id = bip70_id
        self.user_id = user_id

    def __repr__(self):
        """Represent instance as a unique string."""
        return '<blockchain: {}, address: {}, txno: {}, \
total_coins: {}, created_at: {}, user_id: {}, \
received_at: {}, confirmed_at: {}, bip70_id: {}>'.format(
            self.blockchain,
            self.address,
            self.txno,
            self.total_coins,
            self.created_at,
            self.user_id,
            self.received_at,
            self.bip70_id,
            self.confirmed_at
        )


class Basket(SurrogatePK, Model):
    """User basket."""

    __tablename__ = 'basket'
    user_id = Column(db.Integer(), db.ForeignKey('users.id'), nullable=False)
    campaigno = Column(db.Integer(), db.ForeignKey('orders.campaigno'), nullable=False)

    def __init__(self, user_id, campaigno):
        """Create instance."""
        self.user_id = user_id
        self.campaigno = campaigno

    def __repr__(self):
        """Represent instance as a unique string."""
        return 'user_id: {}, campaigno: {}>'.format(
            self.user_id,
            self.campaigno
        )


class Log(SurrogatePK, Model):
    """Operational logging."""

    __tablename__ = 'log'
    user_id = Column(db.Integer(), db.ForeignKey('users.id'), nullable=False)
    datelog = Column(db.DateTime, nullable=False, default=dt.datetime.utcnow)
    logdata = Column(db.Text(), unique=False, nullable=False)

    def __init__(self, user_id, datelog, logdata):
        """Create instance."""
        self.user_id = user_id
        self.datelog = datelog
        self.logdata = logdata

    def __repr__(self):
        """Represent instance as a unique string."""
        return 'user_id: {}, logdata: {}, datelog: {}>'.format(
            self.user_id,
            self.logdata,
            self.datelog
        )
