# -*- coding: utf-8 -*-
"""User and other DB models."""
import uuid
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

#    def __init__(self, username, email, password=None, **kwargs):
#        """Create instance."""
#        db.Model.__init__(self, username=username, email=email, **kwargs)
#        if password:
#            self.set_password(password)
#        else:
#            self.password = None

#    def set_password(self, password):
#        """Set password."""
#        self.password = bcrypt.generate_password_hash(password)

#    def check_password(self, value):
#        """Check password."""
#        return bcrypt.check_password_hash(self.password, value)

#    @property
#    def full_name(self):
#        """Full user name."""
#        return '{0} {1}'.format(self.first_name, self.last_name)

    def __repr__(self):
        """Represent instance as a unique string."""
        return '<User({username!r})>'.format(username=self.username)


class Banner(SurrogatePK, Model):
    """Banner files."""

    __tablename__ = 'banners'
    filename = Column(db.String(256), unique=True, nullable=False)
    owner = Column(db.Integer(), unique=False, nullable=False)
    created_at = Column(db.DateTime, nullable=False, default=dt.datetime.utcnow)
    url = Column(db.String(2083), nullable=False)
    height = Column(db.Integer(), nullable=False)
    width = Column(db.Integer(), nullable=False)
    comments = Column(db.String(512), nullable=True)

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

    def __init__(self,zoneid, dayprice):
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
    zoneid = Column(db.Integer(), unique=False, nullable=False)
    ispaid = Column(db.Boolean(), default=False, nullable=False)
    created_at = Column(db.DateTime, nullable=False, default=dt.datetime.utcnow)
    amount_btc = Column(db.Numeric(16,8))
    btcaddress = Column(db.String(35), unique=True, nullable=False)

    def __init__(self, campaigno, zoneid, ispaid,
                 created_at, amount_btc, btcaddress):
        """Create instance."""
        self.campaigno = campaigno
        self.zoneid = zoneid
        self.ispaid = ispaid
        self.created_at = created_at
        self.amount_btc = amount_btc
        self.btcaddress = btcaddress

    def __repr__(self):
        """Represent instance as a unique string."""
        return '<campaigno: {}, zpneid: {}, ispaid: {}, created_at: {},\
                amount_btc: {}, btcaddress: {}>'.format(
                                            self.campaigno,
                                            self.zoneid,
                                            self.ispaid,
                                            self.created_at,
                                            self.amount_btc,
                                            self.btcaddress)


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
        # return '<zone_id: {}, placement_id: {}>'.format(self.zone_id,
        #                                                self.placement_id)
        return '<zone_id: {}>'.format(self.zone_id)
