# render_template takes a filename and a variable list of template arguments and returns the same template,
# but with all the placeholders in it replaced with actual values.
from flask import render_template, flash, redirect, url_for, request # Accepts and validates data submitted by the user. 
from app import app # Imports the app variable from the app package
from app.forms import LoginForm  # Imports the LoginForm class from forms.py, which contains the form and fields. 
from flask_login import current_user, login_user, logout_user, login_required
from app.models import User
from werkzeug.urls import url_parse
from app import db
from app.forms import RegistrationForm
from datetime import datetime
from app.forms import EditProfileForm
from app.forms import EmptyForm
from app.forms import PostForm
from app.models import Post
from app.forms import ResetPasswordRequestForm
from app.email import send_password_reset_email
from app.forms import ResetPasswordForm 



# View functions are mapped to one or more URL's so that flask knows what loginc to execute
# when a client requests a given url.
# A decorator modifies the function that follows. 
@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
@login_required # This function will not allow users that aren't authenticated.
def index():
	form = PostForm()
	if form.validate_on_submit():
		post = Post(body=form.post.data, author=current_user)
		db.session.add(post)
		db.session.commit()
		flash('Your post is now live!')
		return redirect(url_for('index'))
	page = request.args.get('page', 1, type=int)	
	posts = current_user.followed_posts().paginate(page, app.config['POSTS_PER_PAGE'], False)
	next_url = url_for('index', page=posts.next_num) \
		if posts.has_next else None
	prev_url = url_for('index', page=posts.prev_num) \
		if posts.has_prev else None
	return render_template('index.html', title='Home',form=form, posts=posts.items, next_url=next_url, prev_url=prev_url)


# View function maped to the /login URL that creates a form and passes it to the template
# for rendering. 
@app.route('/login', methods=['GET', 'POST']) # Tells flask this view accepts GET and POST requests, overriding the default GET.
def login():	
	# The current_user variable comes from Flask-Login and can be used at any time during the handling to obtain the user object that represents the
	# client of the request. 
	if current_user.is_authenticated: # Checks if user is logged in or not. 
		return redirect(url_for('index'))  # redirects to index if it is logged in. Do not allow logged in user to go to login page.
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
			return redirect(url_for('login')) # Redirect after a non succesful login. 
		login_user(user, remember=form.remember_me.data) # Both the password and username were correct. login_user(), which comes from flask-login. 
		next_page = request.args.get('next')
		# If the login URL does not have a next argument, then the user is redirected to the index page.
		# If the login URL includes a next argument that is set to a full URL that includes a domain name, then the user is redirected to the index page.
		if not next_page or url_parse(next_page).netloc != '':
			next_page = url_for('index')
		return redirect (next_page) # Redirects the user automatically to the target('index') template.
	return render_template('login.html', title='Sign In', form=form) #form obejct sent to login template.


@app.route('/register', methods=['GET', 'POST'])
def register():
	if current_user.is_authenticated:
		return redirect(url_for('index'))
	form = RegistrationForm()
	if form.validate_on_submit():
		user = User(username=form.username.data, email=form.email.data)
		user.set_password(form.password.data)
		db.session.add(user)
		db.session.commit()
		flash('Congratulations, you are now a registered user!')
		return redirect(url_for('login'))
	return render_template('register.html', title='Register', form=form)


@app.route('/logout')
def logout():
	logout_user()
	return redirect(url_for('index'))


@app.route('/user/<username>')
@login_required
def user(username):
	user = User.query.filter_by(username=username).first_or_404() # Load the user fro the database using a query by username. 
	page = request.args.get('page', 1, type=int)
	posts = user.posts.order_by(Post.timestamp.desc()).paginate(page,
		app.config['POSTS_PER_PAGE'], False)
	next_url = url_for('user', username=user.username, page=posts.next_num) \
		if posts.has_next else None
	prev_url = url_for('user', username=user.username, page=posts.prev_num) \
		if posts.has_prev else None
	form = EmptyForm()
	return render_template('user.html', user=user, posts=posts.items,
	next_url=next_url, prev_url=prev_url, form=form)


#  checks if the current_user is logged in, and in that case sets the last_seen field to the current time
# and is executed before any view function in the application.
@app.before_request
def before_request():
	if current_user.is_authenticated:
		current_user.last_seen = datetime.utcnow()
		db.session.commit() # ommit the database session, so that the change made above is written to the database


@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
	form = EditProfileForm(current_user.username)
	if form.validate_on_submit():
		current_user.username = form.username.data
		current_user.about_me = form.about_me.data
		db.session.commit()
		flash('Your changes have been saved')
		return redirect(url_for('edit_profile'))
	elif request.method == 'GET':
		form.username.data = current_user.username
		form.about_me.data = current_user.about_me
	return render_template('edit_profile.html', title='Edit Profile', form=form)




@app.route('/follow/<username>', methods=['POST'])
@login_required
def follow(username):
	form = EmptyForm()
	if form.validate_on_submit():
		user = User.query.filter_by(username=username).first()
		if user is None:
			flash('User {} not found'.format(username))
			return redirect(url_for('index'))
		if user == current_user:
			flash('You cannot follow yourself!')
			return redirect(url_for('user', username=username))
		current_user.follow(user)
		db.session.commit()
		flash('You are following {}!'.format(username))
		return redirect(url_for('user', username=username))
	else:
		return redirect(url_for('index'))




@app.route('/unfollow/<username>', methods=['POST'])
@login_required
def unfollow(username):
	form = EmptyForm()
	if form.validate_on_submit():
		user = User.query.filter_by(username=username).first()
		if user is None:
			flash('User {} not found'.format(username))
			return redirect(url_for('index'))
		if user == current_user:
			flash('You cannot unfollow yourself!')
			return redirect(url_for('user', username=username))
		current_user.unfollow(user)
		db.session.commit()
		flash('You are not following {}!'.format(username))
		return redirect(url_for('user', username=username))
	else:
		return redirect(url_for('index'))

@app.route('/explore')
@login_required
def explore():
	page = request.args.get('page', 1, type=int)
	posts = Post.query.order_by(Post.timestamp.desc()).paginate(page, app.config['POSTS_PER_PAGE'], False)
	next_url = url_for('explore', page=posts.next_num) \
		if posts.has_next else None
	prev_url = url_for('explore', page=posts.prev_num) \
		if posts.has_prev else None
	return render_template("index.html", title='Explore', posts=posts.items, next_url=next_url, prev_url=prev_url) # items is an attribute of the pagination object, which contains the list of items retrieved for the selected page. 
	# The pagination object also have has_next, has_prev, next_num, prev_num.


@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
	if current_user.is_authenticated:
		return redirect(url_for('index'))
	form = ResetPasswordRequestForm()
	if form.validate_on_submit():
		user = User.query.filter_by(email=form.email.data).first()
		if user:
			send_password_reset_email(user)
		flash('Check your mail for instructions to reset your password!')
		return redirect(url_for('login'))
	return render_template('reset_password_request.html', title='Reset Password', form=form)



@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    user = User.verify_reset_password_token(token) # This method returns the user if the token is valid, or None if not.
    if not user:
        return redirect(url_for('index')) #  If the token is invalid I redirect to the home page.
    # If the token is valid, then I present the user with a second form, in which the new password is requested. 
    # This form is processed in a way similar to previous forms, and as a result of a valid form submission, I invoke the set_password() method of User to change the password, 
    # and then redirect to the login page, where the user can now login.
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been reset.')
        return redirect(url_for('login'))
    return render_template('reset_password.html', form=form)





