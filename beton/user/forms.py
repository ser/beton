# -*- coding: utf-8 -*-
"""User forms."""
from flask_wtf import Form
from flask_wtf.file import FileAllowed, FileField, FileRequired
from flask_uploads import UploadSet, IMAGES
from flask_security import ConfirmRegisterForm
from wtforms import IntegerField, StringField
from wtforms.validators import DataRequired, Length, NumberRange, Required, URL

images = UploadSet('images', IMAGES)


class AddBannerForm(Form):
    """Upload banner form."""

    banner_url = StringField('URL to your advertised page - must include https:// or http://',
                             validators=[DataRequired(), Length(max=2000), URL()])
    banner_comments = StringField('Comments (optional)',
                                  validators=[Length(max=500)])
    banner_image = FileField('Banner image file',
                             validators=[FileRequired(), FileAllowed(images, 'Images only!')])

    def __init__(self, *args, **kwargs):
        """Create instance."""
        super(AddBannerForm, self).__init__(*args, **kwargs)

    # TODO: validate if size of the image is not bigger than 500kb


class AddBannerTextForm(Form):
    """Upload banner form."""

    banner_url = StringField('URL to your advertised page - must include https:// or http://',
                             validators=[DataRequired(), Length(max=2000), URL()])
    banner_content = StringField('Banner text content (20 to 255 characters)',
                                 validators=[DataRequired(), Length(min=20, max=255)])
    banner_comments = StringField('Comments (optional)',
                                  validators=[Length(max=500)])
    banner_icon = StringField('Web Icon',
                              validators=[Length(max=120)])

    def __init__(self, *args, **kwargs):
        """Create instance."""
        super(AddBannerTextForm, self).__init__(*args, **kwargs)

class AddZoneForm(Form):
    """Add zone."""

    zone_name = StringField('Zone name (10 to 100 characters)',
                            validators=[DataRequired(), Length(min=10, max=100)])
    zone_comments = StringField('Description (optional)',
                                validators=[Length(max=500)])
    zone_width = IntegerField('Zone Width in pixels (10-1500)',
                               validators=[DataRequired(), NumberRange(min=10, max=1500)])
    zone_height = IntegerField('Zone Height in pixels (10-1500)',
                               validators=[DataRequired(), NumberRange(min=10, max=1500)])

    def __init__(self, *args, **kwargs):
        """Create instance."""
        super(AddZoneForm, self).__init__(*args, **kwargs)

class AddPairingTextForm(Form):
    """Payment processor pairing form."""

    pairing_code = StringField('Type access token pairing code generated in your payment processor:',
                               validators=[DataRequired(), Length(min=7, max=7)])

    def __init__(self, *args, **kwargs):
        """Create instance."""
        super(AddPairingTextForm, self).__init__(*args, **kwargs)


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
