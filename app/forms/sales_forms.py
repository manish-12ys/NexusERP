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


class CustomerForm(FlaskForm):
    name = StringField("Customer Name", validators=[DataRequired(), Length(max=200)])
    contact_person = StringField("Contact Person", validators=[Optional(), Length(max=120)])
    email = StringField("Email", validators=[Optional(), Email()])
    phone = StringField("Phone", validators=[Optional(), Length(max=20)])
    address = TextAreaField("Address", validators=[Optional()])
    city = StringField("City", validators=[Optional(), Length(max=80)])
    state = StringField("State", validators=[Optional(), Length(max=80)])
    pincode = StringField("Pincode", validators=[Optional(), Length(max=20)])
    gst_number = StringField("GST Number", validators=[Optional(), Length(max=30)])
    credit_limit = FloatField("Maximum Purchase Amount", default=0.0)
    submit = SubmitField("Save")


class SalesOrderForm(FlaskForm):
    customer_id = SelectField("Customer", coerce=int, validators=[DataRequired()])
    expected_date = DateField("Expected Delivery Date", validators=[Optional()])
    notes = TextAreaField("Notes", validators=[Optional()])
    submit = SubmitField("Save")


class SalesOrderLineForm(FlaskForm):
    product_id = SelectField("Product", coerce=int, validators=[DataRequired()])
    quantity = FloatField("Quantity", validators=[DataRequired()])
    unit_price = FloatField("Unit Price", default=0.0)
    submit = SubmitField("Add Line")
