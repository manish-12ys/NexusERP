from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    TextAreaField,
    FloatField,
    SelectField,
    DateField,
    SubmitField,
)
from wtforms.validators import DataRequired, Optional, Email, Length


class SupplierForm(FlaskForm):
    name = StringField("Supplier Name", validators=[DataRequired(), Length(max=200)])
    contact_person = StringField("Contact Person", validators=[Optional(), Length(max=120)])
    email = StringField("Email", validators=[Optional(), Email()])
    phone = StringField("Phone", validators=[Optional(), Length(max=20)])
    address = TextAreaField("Address", validators=[Optional()])
    city = StringField("City", validators=[Optional(), Length(max=80)])
    state = StringField("State", validators=[Optional(), Length(max=80)])
    pincode = StringField("Pincode", validators=[Optional(), Length(max=20)])
    gst_number = StringField("GST Number", validators=[Optional(), Length(max=30)])
    payment_terms = StringField("Payment Terms", validators=[Optional(), Length(max=200)])
    lead_time_days = FloatField("Lead Time (days)", default=0)
    submit = SubmitField("Save")


class VendorForm(SupplierForm):
    pass


class PurchaseOrderForm(FlaskForm):
    vendor_id = SelectField("Supplier", coerce=int, validators=[DataRequired()])
    expected_date = DateField("Expected Delivery Date", validators=[Optional()])
    notes = TextAreaField("Notes", validators=[Optional()])
    submit = SubmitField("Save")
