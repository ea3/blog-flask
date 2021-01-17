from flask import render_template, redirect, url_for, flash, request
from werkzeug.urls import url_parse
from flask_login import login_user, logout_user, current_user
from app import db
from app.auth import bp
from app.auth.forms import LoginForm, RegistrationForm, \
    ResetPasswordRequestForm, ResetPasswordForm
from app.models import User
from app.auth.email import send_password_reset_email


# View functions are mapped to one or more URL's so that flask knows what loginc to execute
# when a client requests a given url.
# A decorator modifies the function that follows. 



# View function maped to the /login URL that creates a form and passes it to the template
# for rendering. 
@bp.route('/login', methods=['GET', 'POST']) # Tells flask this view accepts GET and POST requests, overriding the default GET.
def login():	
	# The current_user variable comes from Flask-Login and can be used at any time during the handling to obtain the user object that represents the
	# client of the request. 
	if current_user.is_authenticated: # Checks if user is logged in or not. 
		return redirect(url_for('main.index'))  # redirects to index if it is logged in. Do not allow logged in user to go to login page.
	form = LoginForm() # Instantiating a LoginForm object that will be later sent to the template with the render_template function.
	
	# When the browser sends the GET request to receive the web page with the form, 
	#this method is going to return False, so in that case the function skips the if statement
	# and goes directly to render the template in the last line of the function.
	# When the browser sends the POST request as a result of the user pressing the submit button, form.validate_on_submit() is going to gather all the data,
	# run all the validators attached to fields, and if everything is all right it will return True, indicating that the data is valid and can be processed by the application.
	# But if at least one field fails validation, then the function will return False, and that will cause the form to be rendered back to the user, like in the GET request case.
	if form.validate_on_submit():  
		#Since I know there is only going to be one or zero results, I complete the query by calling first(), which will return the user object if it exists, or None if it does not.
		user = User.query.filter_by(username=form.username.data).first() # The result of filter_by() is a query that only includes the objects that have a matching username.
		if user is None or not user.check_password(form.password.data): # If username is invalid or password is incorrect for the user..
			flash('Invalid username or password') # shows a message to the user. 
			return redirect(url_for('auth.login')) # Redirect after a non succesful login. 
		login_user(user, remember=form.remember_me.data) # Both the password and username were correct. login_user(), which comes from flask-login. 
		next_page = request.args.get('next')
		# If the login URL does not have a next argument, then the user is redirected to the index page.
		# If the login URL includes a next argument that is set to a full URL that includes a domain name, then the user is redirected to the index page.
		if not next_page or url_parse(next_page).netloc != '':
			next_page = url_for('main.index')
		return redirect (next_page) # Redirects the user automatically to the target('index') template.
	return render_template('auth/login.html', title='Sign In', form=form) #form obejct sent to login template.

@bp.route('/logout')
def logout():
	logout_user()
	return redirect(url_for('main.index'))


@bp.route('/register', methods=['GET', 'POST'])
def register():
	if current_user.is_authenticated:
		return redirect(url_for('main.index'))
	form = RegistrationForm()
	if form.validate_on_submit():
		user = User(username=form.username.data, email=form.email.data)
		user.set_password(form.password.data)
		db.session.add(user)
		db.session.commit()
		flash('Congratulations, you are now a registered user!')
		return redirect(url_for('auth.login'))
	return render_template('auth/register.html', title='Register', form=form)



@bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
	if current_user.is_authenticated:
		return redirect(url_for('main.index'))
	form = ResetPasswordRequestForm()
	if form.validate_on_submit():
		user = User.query.filter_by(email=form.email.data).first()
		if user:
			send_password_reset_email(user)
		flash('Check your mail for instructions to reset your password!')
		return redirect(url_for('auth.login'))
	return render_template('auth/reset_password_request.html', title='Reset Password', form=form)



@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    user = User.verify_reset_password_token(token) # This method returns the user if the token is valid, or None if not.
    if not user:
        return redirect(url_for('main.index')) #  If the token is invalid I redirect to the home page.
    # If the token is valid, then I present the user with a second form, in which the new password is requested. 
    # This form is processed in a way similar to previous forms, and as a result of a valid form submission, I invoke the set_password() method of User to change the password, 
    # and then redirect to the login page, where the user can now login.
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been reset.')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)


