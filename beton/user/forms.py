# -*- coding: utf-8 -*-
"""User forms."""
from flask_wtf import Form
from flask_wtf.file import FileAllowed, FileField, FileRequired
from flask_uploads import UploadSet, IMAGES
from flask_security import ConfirmRegisterForm
from wtforms import IntegerField, StringField
from wtforms.validators import DataRequired, Length, Required

images = UploadSet('images', IMAGES)


class AddBannerForm(Form):
    """Upload banner form."""

    banner_url = StringField('URL to your advertised page',
                             validators=[DataRequired(), Length(min=10, max=2000)])
    banner_comments = StringField('Comments (optional)')
    banner_image = FileField('Banner image file',
                             validators=[FileRequired(), FileAllowed(images, 'Images only!')])

    def __init__(self, *args, **kwargs):
        """Create instance."""
        super(AddBannerForm, self).__init__(*args, **kwargs)

    # TODO: validate if size of the image is not bigger than 500kb


class ChangeOffer(Form):
    """Modify zone prices."""
    zoneprice = IntegerField('Price per day')
    zoneid = IntegerField('Zone ID')
    x0 = IntegerField('x0')
    y0 = IntegerField('y0')
    x1 = IntegerField('x1')
    y1 = IntegerField('y1')

    def __init__(self, *args, **kwargs):
        """Create instance."""
        super(ChangeOffer, self).__init__(*args, **kwargs)


class ExtendedConfirmRegisterForm(ConfirmRegisterForm):
    '''user registration'''
    username = StringField('Username', [Required()])
