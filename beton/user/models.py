# -*- coding: utf-8 -*-
"""User and other DB models."""
import datetime as dt

from flask_sqlalchemy import SQLAlchemy
from flask_user import UserMixin

from beton.database import Column, Model, SurrogatePK, reference_col, relationship

db = SQLAlchemy()


class Role(SurrogatePK, Model):
    """A role for a user."""

    __tablename__ = 'roles'
    name = Column(db.String(80), unique=True, nullable=False)
    user_id = reference_col('users', nullable=True)
    user = relationship('User', backref='roles')

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
    email = Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False, default='')
    confirmed_at = Column(db.DateTime, nullable=True)
    first_name = Column(db.String(30), nullable=True)
    last_name = Column(db.String(30), nullable=True)
    is_enabled = Column(db.Boolean(), default=False)

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
        return '<filename: {}, owner: {}, created_at: {}, url: {}, height: {},\
                width: {}, comment: {}>'.format(self.filename, self.owner,
                                                self.created_at,
                                                self.url, self.height,
                                                self.width, self.comments)


class Prices(SurrogatePK, Model):
    """Zone prices"""

    __tablename__ = 'zoneprice'
    zoneid = Column(db.Integer(), unique=True, nullable=False)
    dayprice = Column(db.Integer(), unique=False, nullable=False)

    def __init__(self, zoneid, dayprice):
        """Create instance."""
        self.zoneid = zoneid
        self.dayprice = dayprice

    def __repr__(self):
        """Represent instance as a unique string."""
        return '<zoneid: {}, dayprice: {}>'.format(self.zoneid,
                                                   self.dayprice)


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

    def __init__(self, campaigno, zoneid, created_at, begins_at,
                 stops_at, paymentno, bannerid):
        """Create instance."""
        self.campaigno = campaigno
        self.zoneid = zoneid
        self.created_at = created_at
        self.begins_at = begins_at
        self.stops_at = stops_at
        self.paymentno = paymentno
        self.bannerid = bannerid

    def __repr__(self):
        """Represent instance as a unique string."""
        return '<campaigno: {}, zoneid: {}, created_at: {},\
                begins_at: {}, stops_at: {},\
                paymentno: {}, bannerid: {}>'.format(
                                        self.campaigno,
                                        self.zoneid,
                                        self.created_at,
                                        self.begins_at,
                                        self.stops_at,
                                        self.paymentno,
                                        self.bannerid)


class Payments(SurrogatePK, Model):
    """All payments"""

    __tablename__ = 'payments'
    blockchain = Column(db.String(10), unique=False, nullable=False)
    address = Column(db.String(64), unique=True, nullable=False)
    total_coins = Column(db.Numeric(16, 8))
    txno = Column(db.String(64), unique=False, nullable=True)
    created_at = Column(db.DateTime, nullable=False, default=dt.datetime.utcnow)

    def __init__(self, blockchain, address, txno, total_coins, created_at):
        """ Create instance."""
        self.blockchain = blockchain
        self.address = address
        self.txno = txno
        self.total_coins = total_coins
        self.created_at = created_at

    def __repr__(self):
        """Represent instance as a unique string."""
        return '<blockchain: {}, address: {}, txno: {},\
                total_coins: {}, created_at: {}>'.format(
                                self.blockchain,
                                self.address,
                                self.txno,
                                self.total_coins,
                                self.created_at)


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
                                self.campaigno)


class Zone2Campaign(Model):
    """Relation from original DB, a quick hack."""

    __bind_key__ = 'revive'
    __tablename__ = 'rv_placement_zone_assoc'
    placement_zone_assoc_id = Column(db.Integer(), unique=True,
                                     primary_key=True, nullable=False)
    zone_id = Column(db.Integer(), nullable=True, unique=False)
    placement_id = Column(db.Integer(), nullable=True, unique=False)

    def __init__(self, zone_id, placement_id):
        """Create instance."""
        self.zone_id = zone_id
        self.placement_id = placement_id

    def __repr__(self):
        """Represent instance as a unique string."""
        return '<zone_id: {}>'.format(self.zone_id)
