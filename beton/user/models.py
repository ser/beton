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
    bannerid = db.relationship("Orders")

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
    zoneid = Column(db.Integer(), db.ForeignKey('zoneprice.zoneid', ondelete='CASCADE'), nullable=False)
    created_at = Column(db.DateTime, nullable=False, default=dt.datetime.utcnow)
    begins_at = Column(db.DateTime, nullable=False, default=dt.datetime.utcnow)
    stops_at = Column(db.DateTime, nullable=False, default=dt.datetime.utcnow)
    paymentno = Column(db.Integer(), unique=False, nullable=True)
    bannerid = Column(db.Integer(), db.ForeignKey('banners.id', ondelete='CASCADE'), nullable=False)
    name = Column(db.Text, unique=False, nullable=False)
    comments = Column(db.Text, unique=False, nullable=False)
    impressions = Column(db.Integer(), unique=False, nullable=True)
    user_id = Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

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
    created_at = Column(db.DateTime, nullable=False, default=dt.datetime.utcnow)
    received_at = Column(db.DateTime, nullable=False)
    confirmed_at = Column(db.DateTime, nullable=False)
    btcpayserver_id = Column(db.String(22), nullable=False)
    posdata = Column(db.String(36), nullable=False)
    fiat = Column(db.String(3), unique=False, nullable=False)
    fiat_amount = Column(db.Numeric(16, 8), nullable=False)
    user_id = Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    def __init__(self, fiat, fiat_amount, created_at, posdata,
                 received_at, confirmed_at, btcpayserver_id, user_id):
        """ Create instance."""
        self.fiat = fiat
        self.fiat_amount = fiat_amount
        self.created_at = created_at
        self.posdata = posdata
        self.received_at = received_at
        self.confirmed_at = confirmed_at
        self.btcpayserver_id = btcpayserver_id
        self.user_id = user_id

    def __repr__(self):
        """Represent instance as a unique string."""
        return '<fiat: {}, fiat_amount: {}, \
created_at: {}, user_id: {}, posdata: {} \
received_at: {}, confirmed_at: {}, btcpayserver_id: {}>'.format(
            self.fiat,
            self.fiat_amount,
            self.created_at,
            self.user_id,
            self.posdata,
            self.received_at,
            self.confirmed_at,
            self.btcpayserver_id
        )


class Basket(SurrogatePK, Model):
    """User basket."""

    __tablename__ = 'basket'
    user_id = Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    campaigno = Column(db.Integer(), db.ForeignKey('orders.campaigno', ondelete='CASCADE'), nullable=False)

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
        return 'user_id: {}, logdata: {}, datelog: {}>'.format(
            self.user_id,
            self.logdata,
            self.datelog
        )


class Impressions(SurrogatePK, Model):
    """Impressions cache"""

    __tablename__ = 'impressions'
    zoneid = Column(db.Integer(), db.ForeignKey('zoneprice.zoneid', ondelete='CASCADE'), nullable=False)
    impressions = Column(db.Integer(), unique=False, nullable=True)
    clicks = Column(db.Integer(), unique=False, nullable=True)

    def __init__(self, zoneid, impressions, clicks):
        """Create instance."""
        self.zoneid = zoneid
        self.impressions = impressions
        self.clicks = clicks

    def __repr__(self):
        """Represent instance as a unique string."""
        return 'zoneid: {}, impressions: {}, clicks: {}>'.format(
            self.zoneid,
            self.impressions,
            self.clicks
        )
