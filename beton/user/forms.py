# -*- coding: utf-8 -*-
"""User forms."""
from flask_wtf import Form
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import PasswordField, StringField
from wtforms.validators import DataRequired, Email, EqualTo, Length

from beton.extensions import images

from .models import User


class RegisterForm(Form):
    """Register form."""

    username = StringField('Username',
                           validators=[DataRequired(), Length(min=3, max=25)])
    email = StringField('Email',
                        validators=[DataRequired(), Email(), Length(min=6, max=40)])
    password = PasswordField('Password',
                             validators=[DataRequired(), Length(min=6, max=40)])
    confirm = PasswordField('Verify password',
                            [DataRequired(), EqualTo('password', message='Passwords must match')])

    def __init__(self, *args, **kwargs):
        """Create instance."""
        super(RegisterForm, self).__init__(*args, **kwargs)
        self.user = None

    def validate(self):
        """Validate the form."""
        initial_validation = super(RegisterForm, self).validate()
        if not initial_validation:
            return False
        user = User.query.filter_by(username=self.username.data).first()
        if user:
            self.username.errors.append('Username already registered')
            return False
        user = User.query.filter_by(email=self.email.data).first()
        if user:
            self.email.errors.append('Email already registered')
            return False
        return True


class AddBannerForm(Form):
    """Upload banner form."""

    banner_url = StringField('URL to your advertised page',
                             validators=[DataRequired(), Length(min=10, max=2000)])
    banner_comment = StringField('Comments (optional)')
    banner_image = FileField('Banner image file',
                             validators=[FileRequired(), FileAllowed(images, 'Images only!')])

    def __init__(self, *args, **kwargs):
        """Create instance."""
        super(AddBannerForm, self).__init__(*args, **kwargs)

    # TODO: validate if size of the image is not bigger than 500kb
