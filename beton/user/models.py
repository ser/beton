# -*- coding: utf-8 -*-
"""User and other DB models."""
# import uuid
import datetime as dt

from flask_user import UserMixin

from beton.database import Column, Model, SurrogatePK, db, reference_col, relationship


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
    amount_days = Column(db.Integer(), unique=False, nullable=False)
    paymentno = Column(db.Integer(), unique=False, nullable=True)
    bannerid = Column(db.Integer(), db.ForeignKey('banners.id'), nullable=False)

    def __init__(self, campaigno, zoneid, created_at, amount_days,
                 paymentno, bannerid):
        """Create instance."""
        self.campaigno = campaigno
        self.zoneid = zoneid
        self.created_at = created_at
        self.amount_days = amount_days
        self.paymentno = paymentno
        self.bannerid = bannerid

    def __repr__(self):
        """Represent instance as a unique string."""
        return '<campaigno: {}, zoneid: {}, created_at: {},\
                amount_days: {}, paymentno: {}, bannerid: {}>'.format(
                                        self.campaigno,
                                        self.zoneid,
                                        self.created_at,
                                        self.amount_days,
                                        self.paymentno,
                                        self.bannerid)


class Payments(SurrogatePK, Model):
    """All payments"""

    __tablename__ = 'payments'
    paymentno = Column(db.Integer(), unique=True, nullable=False)
    btcaddress = Column(db.String(35), unique=True, nullable=False)
    total_btc = Column(db.Numeric(16, 8))
    ispaid = Column(db.Boolean(), default=False, nullable=False)
    created_at = Column(db.DateTime, nullable=False, default=dt.datetime.utcnow)

    def __init__(self, paymentno, btcaddress, total_btc, ispaid, created_at):
        """ Create instance."""
        self.paymentno = paymentno
        self.btcaddress = btcaddress
        self.ispaid = ispaid
        self.total_btc = total_btc
        self.created_at = created_at

    def __repr__(self):
        """Represent instance as a unique string."""
        return '<paymentno: {}, btcaddress: {}, self.ispaid: {}, \
                total_btc: {}, created_at: {}>'.format(
                                self.paymentno,
                                self.btcaddress,
                                self.ispaid,
                                self.total_btc,
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
