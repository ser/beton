# -*- coding: utf-8 -*-
"""User forms."""
from flask_wtf import Form
from flask_wtf.file import FileAllowed, FileField, FileRequired
from flask_uploads import UploadSet, IMAGES
from flask_security import ConfirmRegisterForm
from wtforms import BooleanField, HiddenField, IntegerField, SelectField, StringField
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
    banner_width = IntegerField('Width (50-960)',
                                validators=[DataRequired(), NumberRange(min=50, max=960)])
    banner_height = IntegerField('Height (50-960)',
                                validators=[DataRequired(), NumberRange(min=50, max=960)])
    banner_content_line1 = StringField('1st line',
                                 validators=[DataRequired(), Length(min=0, max=50)])
    banner_content_line2 = StringField('2nd line',
                                 validators=[DataRequired(), Length(min=0, max=50)])
    banner_content_line3 = StringField('3rd line',
                                 validators=[DataRequired(), Length(min=0, max=50)])
    banner_content_line4 = StringField('4th line',
                                 validators=[DataRequired(), Length(min=0, max=50)])
    banner_content_line5 = StringField('5th line',
                                 validators=[DataRequired(), Length(min=0, max=50)])
    banner_comments = StringField('Comments (optional)',
                                  validators=[Length(max=500)])

    def __init__(self, *args, **kwargs):
        """Create instance."""
        super(AddBannerTextForm, self).__init__(*args, **kwargs)

class AddZoneForm(Form):
    """Add zone."""

    zone_website = SelectField('Choose website:', coerce=int)

    zone_name = StringField('Zone name (10 to 100 characters)',
                            validators=[DataRequired(), Length(min=10, max=100)])
    zone_comments = StringField('Description (optional)',
                                validators=[Length(max=500)])
    zone_width = IntegerField('Width (10-1500)',
                               validators=[DataRequired(), NumberRange(min=10, max=1500)])
    zone_height = IntegerField('Height (10-1500)',
                               validators=[DataRequired(), NumberRange(min=10, max=1500)])
    zone_x0 = IntegerField('x0', validators=[NumberRange(min=0, max=1500)],
                                             default=0)
    zone_x1 = IntegerField('x1', validators=[NumberRange(min=0, max=1500)],
                                             default=0)
    zone_y0 = IntegerField('y0', validators=[NumberRange(min=0, max=1500)],
                                             default=0)
    zone_y1 = IntegerField('y1', validators=[NumberRange(min=0, max=1500)],
                                             default=0)
    zone_active = BooleanField('active')

    edited = HiddenField()

    def __init__(self, *args, **kwargs):
        """Create instance."""
        super(AddZoneForm, self).__init__(*args, **kwargs)


class AddWebsiteForm(Form):
    """Add website."""

    website_name = StringField('Website name (10 to 100 characters)',
                            validators=[DataRequired(), Length(min=10, max=100)])
    website_comments = StringField('Description (optional)',
                                validators=[Length(max=500)])
    website_active = BooleanField('active', default='checked')

    def __init__(self, *args, **kwargs):
        """Create instance."""
        super(AddWebsiteForm, self).__init__(*args, **kwargs)


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

    def __init__(self, *args, **kwargs):
        """Create instance."""
        super(ChangeOffer, self).__init__(*args, **kwargs)


class ExtendedConfirmRegisterForm(ConfirmRegisterForm):
    '''user registration'''
    username = StringField('Username', [Required()])
