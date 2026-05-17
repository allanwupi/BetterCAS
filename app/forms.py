from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo

# Login form used for user authentication
class LoginForm(FlaskForm):

    # Accept either email or username
    identifier = StringField(
        'Email or username',
        validators=[DataRequired()],
        render_kw={'placeholder': 'you@example.com'}
    )

    password = PasswordField(
        'Password',
        validators=[DataRequired()],
        render_kw={'placeholder': 'Enter your password'}
    )
    # Keeps the user logged in between browser sessions 
    remember = BooleanField('Remember Me')

    submit = SubmitField('Login')

# Signup form used for creating new accounts
class SignupForm(FlaskForm):

    username = StringField(
        'Username',
        validators=[DataRequired()],
        render_kw={'placeholder': 'Choose a username'}
    )

    email = StringField(
        'Email',
        validators=[
            DataRequired(),
            Email()
        ],
        render_kw={'placeholder': 'you@example.com'}
    )

    # Password must be a minimum of 8 characters
    password = PasswordField(
        'Password',
        validators=[
            DataRequired(),
            Length(min=8)
        ],
        render_kw={'placeholder': 'At least 8 characters'}
    )

    confirm_password = PasswordField(
        'Confirm password',
        validators=[
            DataRequired(),
            EqualTo('password')
        ],
        render_kw={'placeholder': 'Re-enter password'}
    )

    submit = SubmitField('Sign up')
