from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired, Length

class register(FlaskForm):
    name = StringField('username', validators=[DataRequired(), Length(max=64)])
    password = PasswordField('password', validators=[DataRequired()])
    submit = SubmitField('register')

class login(FlaskForm):
    username = StringField('username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('login')
