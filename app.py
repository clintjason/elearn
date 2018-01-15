from flask import Flask, render_template, url_for, redirect,session,flash, request
import os
from wtforms import Form, StringField, PasswordField, TextAreaField, FileField, SelectField, BooleanField
from wtforms.validators import InputRequired, Email, EqualTo, Length
from flask_mysqldb import MySQL
from passlib.hash import sha256_crypt
from functools import wraps
from data import Courses
from prerequisite import Prerequisite
from collections import Counter
from wtforms.fields.html5 import TelField
from werkzeug import secure_filename

app = Flask(__name__)
app.secret_key = os.urandom(24)

#config Mysql
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'your_user_name'
app.config['MYSQL_PASSWORD'] = 'your_password'
app.config['MYSQL_DB'] = 'elearn'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor' # setting the cursor to return a dictionary rather than a tuple

#initial Mysql Config
mysql = MySQL(app)
UPLOAD_FOLDER = '/home/jason/Projects/elearn/static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER 

@app.route('/')
def home():
	return render_template('home.html')

#create form register learner form field
class RegisterLearner(Form):
	username = StringField('Username', validators=[InputRequired()])
	email = StringField('Email', validators=[InputRequired(),Email()])
	password = PasswordField('Password', validators=[InputRequired(), Length(min=4,max=12), EqualTo('confirm_password',message='passwords do not match')])
	confirm_password = PasswordField('Confirm Password',validators=[InputRequired(),Length(min=4,max=12)])

@app.route('/learner_register', methods=['GET','POST'])
def register_learner():
	form = RegisterLearner(request.form)	#instantiate form
	if request.method == 'POST' and form.validate():
		# Get form inputs
		username = form.username.data
		email = form.email.data
		password = form.password.data

		# create cursor
		cursor = mysql.connection.cursor()

		#check if user exist

		q_result = cursor.execute("SELECT * FROM learners WHERE username = %s", [username])
		if q_result > 0:
			flash('Username Unavailable','danger')
			return redirect(url_for('register_learner'))
		else:
			#encrypt password
			encrypted_password = sha256_crypt.encrypt(str(password))
			result = cursor.execute("INSERT INTO learners (username,email,password) VALUES (%s,%s,%s)", (username,email, encrypted_password))
			mysql.connection.commit()
			cursor.close() # close connection

			#use flash to define and render a response message
			flash('Registration Successful, Please Login', 'success')
			return redirect(url_for('login_learner'))
		
	else:
		return render_template('learner/register.html', form=form)

class LoginLearner(Form):
	username = StringField('Username', validators=[InputRequired()])
	password = PasswordField('Password', validators=[InputRequired()])

@app.route('/learner_login', methods=['GET','POST'])
def login_learner():
	form = LoginLearner(request.form)	#instantiate form
	if request.method == 'POST' and form.validate():
		#get inputs
		username = form.username.data
		candidate_password = form.password.data

		#create cursor
		cursor = mysql.connection.cursor()

		#check if username is valid
		result = cursor.execute("SELECT * FROM learners WHERE username = %s", [username])
		if result > 0:
			#get password from db
			data = cursor.fetchone()
			password = data['password']
			app.logger.info(password)
			
			#compare passwords
			if sha256_crypt.verify(candidate_password, password):
				#start user session
				session['username'] = username
				session['learner_logged_in'] = True
				#flash('You are now Logged in','success')
				return redirect(url_for('home'))
			else:
				flash('Invalid Password','danger')
				return redirect(url_for('login_learner'))

		else:
			flash('Unknown Username','danger')
			return redirect(url_for('login_learner'))

		#close connection
		cursor.close()
	else:
		return render_template('learner/login.html', form=form)

#Decorator to check if userlearner is logged in
def is_learner_logged_in(f):
	@wraps(f)
	def wrap(*args, **kwargs):
		if 'learner_logged_in' in session:
			return f(*args, **kwargs)
		else:
			flash('Unauthorized Access, Please Login','danger')
			return redirect(url_for('login_learner'))
	return wrap

@app.route('/learner_logout', methods=['GET','POST'])
@is_learner_logged_in
def logout_learner():
	session.clear()	# clear session
	flash('You are logged out', 'success')
	return redirect(url_for('login_learner'))

class LearnerEditProfileForm(Form):
	username  = StringField('Username', validators=[InputRequired()])
	email = StringField('Email', validators=[InputRequired(),Email()])
	password = PasswordField('Password', validators=[InputRequired(), Length(min=4,max=12), EqualTo('confirm_password',message='passwords do not match')])
	confirm_password = PasswordField('Confirm Password',validators=[InputRequired(),Length(min=4,max=12)])

@app.route('/learner_edit_profile', methods=['GET','POST'])
@is_learner_logged_in
def edit_profile_learner():
	form = LearnerEditProfileForm(request.form)	#instantiate form
	if request.method == 'POST' and form.validate():
		# Get form inputs
		username = form.username.data
		email = form.email.data
		password = form.password.data

		# create cursor
		cursor = mysql.connection.cursor()

		#encrypt password entry
		encrypted_password = sha256_crypt.encrypt(str(password))
		try:
			result = cursor.execute("UPDATE learners SET username = %s, email=%s, password=%s WHERE username=%s", (username,email, encrypted_password, session['username']))
		except:
			flash('Unauthorized Username', 'danger')
			return redirect(url_for('edit_profile_learner'))
		#commit changes
		mysql.connection.commit()
		cursor.close() # close connection
		#use flash to define and render a response message
		flash('User Details Successfully Updated', 'success')
		return redirect(url_for('edit_profile_learner'))
		
	else:
		return render_template('learner/edit_profile.html', form=form)

@app.route('/learner_notification', methods=['GET','POST'])
@is_learner_logged_in
def notification_learner():
	return render_template('learner/notification.html')

@app.route('/learner_analyze_skill_gap', methods=['GET','POST'])
@is_learner_logged_in
def analyze_skill_gap_learner():
	courses = Courses()
	if request.method=='POST':
		select = request.form.get('select_form') # get selected value
		app.logger.info(select)
		#Get prerequisites of course submitted
		prerequisites = Prerequisite() # get array
		for dic in prerequisites:
			for key, value in dic.iteritems():
				if key == select:
					app.logger.info("key is " + key)
					app.logger.info("Select is " + select)
					app.logger.info(value)
					return redirect(url_for('check_process_learner',value=value,key=key))
				else:
					app.logger.info("UnMatched Entry")
		
	return render_template('learner/analyze_skill_gap.html', courses=courses)

@app.route('/learner_check_process/<string:value>/<string:key>', methods=['GET','POST'])
@is_learner_logged_in
def check_process_learner(value,key):
	prerequisites = Prerequisite()
	if request.method == 'POST':
		result = request.form.getlist('check')	#get check field values		
		app.logger.info(result) #console log the list returned from the check actual state display
		checked_list = [str(r) for r in result]  #convert unicode list to string list
		app.logger.info(checked_list)
		# now compare the list in result with value:that was passed to this route
		app.logger.info("The passed list value") #console log
		app.logger.info(value) # console log the passed list
		#now compare the checked list with the passed list
		# create a list to predefine results
		if key == "Learn Bootstrap":
			unchecked = ['HTML','HTML5','CSS']
		elif key == "Learn AJax":
			unchecked = ['JQuery']
		else:
			unchecked = ""
		return render_template('learner/analyze_skill_gap.html',unchecked =unchecked)

	return render_template('learner/analyze_skill_gap.html', value=value,prerequisites=prerequisites,key=key)

@app.route('/test',methods=['GET','POST'])
def test():
	prerequisites = Prerequisite() # get array
	return render_template('test.html',prerequisites=prerequisites)

#create form register learner form field
class RegisterTutor(Form):
	username = StringField('Username', validators=[InputRequired()])
	email = StringField('Email', validators=[InputRequired(),Email()])
	password = PasswordField('Password', validators=[InputRequired(), Length(min=4,max=12), EqualTo('confirm_password',message='passwords do not match')])
	confirm_password = PasswordField('Confirm Password',validators=[InputRequired(),Length(min=4,max=12)])

#create form register learner form field
class RegisterStudent(Form):
	username = StringField('Username', validators=[InputRequired()])
	email = StringField('Email', validators=[InputRequired(),Email()])
	password = PasswordField('Password', validators=[InputRequired(), Length(min=4,max=12), EqualTo('confirm_password',message='passwords do not match')])
	confirm_password = PasswordField('Confirm Password',validators=[InputRequired(),Length(min=4,max=12)])

@app.route('/tutor_student_home', methods=['GET','POST'])
def tutor_student_home():
	tutor_form = RegisterTutor(request.form)
	student_form = RegisterStudent(request.form)
	return render_template('tutor-student/home.html',tutor_form=tutor_form,student_form=student_form)

@app.route('/tutor_register', methods=['GET','POST'])
def register_tutor():
	tutor_form = RegisterTutor(request.form)
	student_form = RegisterStudent(request.form)
	form = RegisterTutor(request.form)	#instantiate form
	if request.method == 'POST' and form.validate():
		# Get form inputs
		username = form.username.data
		email = form.email.data
		password = form.password.data

		# create cursor
		cursor = mysql.connection.cursor()

		#check if user exist

		q_result = cursor.execute("SELECT * FROM users WHERE username = %s AND is_tutor='True' ", [username])
		if q_result > 0:
			flash('Username Unavailable','danger')
			return redirect(url_for('tutor_student_home'))
		else:
			#encrypt password
			encrypted_password = sha256_crypt.encrypt(str(password))
			result = cursor.execute("INSERT INTO users (username,email,password,is_tutor) VALUES (%s,%s,%s,%s)", (username,email, encrypted_password, True))
			mysql.connection.commit()
			cursor.close() # close connection

			#use flash to define and render a response message
			flash('Registration Successful, Please Login', 'success')
			return redirect(url_for('login_tutor'))
	else:
		return render_template('tutor-student/home.html',tutor_form=tutor_form,student_form=student_form)

class LoginTutor(Form):
	username = StringField('Username', validators=[InputRequired()])
	password = PasswordField('Password', validators=[InputRequired()])

@app.route('/tutor_login', methods=['GET','POST'])
def login_tutor():
	form = LoginTutor(request.form)	#instantiate form
	if request.method == 'POST' and form.validate():
		#get inputs
		username = form.username.data
		candidate_password = form.password.data

		#create cursor
		cursor = mysql.connection.cursor()

		#check if username is valid
		result = cursor.execute("SELECT * FROM users WHERE username = %s AND is_tutor = %s", [username,True])
		if result > 0:
			#get password from db
			data = cursor.fetchone()
			password = data['password']
			app.logger.info(password)
			
			#compare passwords
			if sha256_crypt.verify(candidate_password, password):
				#start user session
				session['username'] = username
				session['tutor_logged_in'] = True
				#flash('You are now Logged in','success')
				return redirect(url_for('edit_profile_tutor'))
			else:
				flash('Invalid Password','danger')
				return redirect(url_for('login_tutor'))

		else:
			flash('Unknown Username','danger')
			return redirect(url_for('login_tutor'))

		#close connection
		cursor.close()
	else:
		return render_template('tutor-student/login_tutor.html', form=form)

#Decorator to check if userlearner is logged in
def is_tutor_logged_in(f):
	@wraps(f)
	def wrap(*args, **kwargs):
		if 'tutor_logged_in' in session:
			return f(*args, **kwargs)
		else:
			flash('Unauthorized Access, Please Login','danger')
			return redirect(url_for('login_tutor'))
	return wrap


@app.route('/student_register', methods=['GET','POST'])
def register_student():
	tutor_form = RegisterTutor(request.form)
	student_form = RegisterStudent(request.form)
	form = RegisterStudent(request.form)	#instantiate form
	if request.method == 'POST' and form.validate():
		# Get form inputs
		username = form.username.data
		email = form.email.data
		password = form.password.data

		# create cursor
		cursor = mysql.connection.cursor()

		#check if user exist

		q_result = cursor.execute("SELECT * FROM users WHERE username = %s AND is_student='True' ", [username])
		if q_result > 0:
			flash('Username Unavailable','danger')
			return redirect(url_for('tutor_student_home'))
		else:
			#encrypt password
			encrypted_password = sha256_crypt.encrypt(str(password))
			result = cursor.execute("INSERT INTO users (username,email,password,is_student) VALUES (%s,%s,%s,%s)", (username,email, encrypted_password, True))
			mysql.connection.commit()
			cursor.close() # close connection

			#use flash to define and render a response message
			flash('Registration Successful, Please Login', 'success')
			return redirect(url_for('login_student'))
	else:
		return render_template('tutor-student/home.html',tutor_form=tutor_form,student_form=student_form)

class LoginStudent(Form):
	username = StringField('Username', validators=[InputRequired()])
	password = PasswordField('Password', validators=[InputRequired()])

@app.route('/student_login', methods=['GET','POST'])
def login_student():
	form = LoginStudent(request.form)	#instantiate form
	if request.method == 'POST' and form.validate():
		#get inputs
		username = form.username.data
		candidate_password = form.password.data

		#create cursor
		cursor = mysql.connection.cursor()

		#check if username is valid
		result = cursor.execute("SELECT * FROM users WHERE username = %s AND is_student = %s", [username,True])
		if result > 0:
			#get password from db
			data = cursor.fetchone()
			password = data['password']
			app.logger.info(password)
			
			#compare passwords
			if sha256_crypt.verify(candidate_password, password):
				#start user session
				session['username'] = username
				session['student_logged_in'] = True
				#flash('You are now Logged in','success')
				return redirect(url_for('edit_profile_student'))
			else:
				flash('Invalid Password','danger')
				return redirect(url_for('login_student'))

		else:
			flash('Unknown Username','danger')
			return redirect(url_for('login_student'))

		#close connection
		cursor.close()
	else:
		return render_template('tutor-student/login_student.html', form=form)

class TutorEditProfileForm(Form):
	username  = StringField('Username', validators=[InputRequired()])
	email = StringField('Email', validators=[InputRequired(),Email()])
	password = PasswordField('Password', validators=[InputRequired(), Length(min=4,max=12), EqualTo('confirm_password',message='passwords do not match')])
	confirm_password = PasswordField('Confirm Password',validators=[InputRequired(),Length(min=4,max=12)])

@app.route('/tutor_edit_profile',methods=['GET','POST'])
@is_tutor_logged_in
def edit_profile_tutor():
	form = TutorEditProfileForm(request.form)	#instantiate form
	if request.method == 'POST' and form.validate():
		# Get form inputs
		username = form.username.data
		email = form.email.data
		password = form.password.data

		# create cursor
		cursor = mysql.connection.cursor()

		#encrypt password entry
		encrypted_password = sha256_crypt.encrypt(str(password))
		try:
			result = cursor.execute("UPDATE users SET username = %s, email=%s, password=%s WHERE username=%s and is_tutor=%s", (username,email, encrypted_password, session['username'], True))
		except:
			flash('Unauthorized Username', 'danger')
			return redirect(url_for('edit_profile_tutor'))
		#commit changes
		mysql.connection.commit()
		cursor.close() # close connection
		#use flash to define and render a response message
		flash('Tutor Details Successfully Updated', 'success')
		return redirect(url_for('edit_profile_tutor'))
		
	else:
		return render_template('tutor-student/tutor/edit_profile.html', form=form)

class TutorDescription(Form):
	tel = TelField('Phone Number',validators=[InputRequired()])
	description = TextAreaField('Education and Experiece', validators=[InputRequired()])
	country = StringField('Country',validators=[InputRequired()])
	language = StringField('Main Language Spoken', validators=[InputRequired()])

@app.route('/tutor_description', methods=['GET','POST'])
@is_tutor_logged_in
def description_tutor():
	form = TutorDescription(request.form)
	if request.method == 'POST' and form.validate():
		# Get form inputs
		tel = form.tel.data
		description = form.description.data
		country = form.country.data
		language = form.language.data
		# create cursor
		cursor = mysql.connection.cursor()
		try:
			result = cursor.execute("UPDATE users set tel=%s, description=%s, country=%s, language=%s WHERE username=%s and is_tutor=%s", [tel, description, country, language, session['username'],True])
		except:
			flash('Update Unsuccessful', 'danger')
			return redirect(url_for('description_tutor'))
		#commit changes
		mysql.connection.commit()
		cursor.close() # close connection
		#use flash to define and render a response message
		flash('User Details Successfully Updated', 'success')
		return redirect(url_for('description_tutor'))
	else:
		return render_template('tutor-student/tutor/_description.html',form=form)

@app.route('/tutor_preferences', methods=['GET','POST'])
@is_tutor_logged_in
def preferences_tutor():
	if request.method == 'POST':
		#get form fields
		location = request.form['location']
		app.logger.info(location)
		if request.form["option"]== 'Online Teaching':
			option1 = request.form["option"]
			app.logger.info(option1)
			cursor = mysql.connection.cursor()
			try:
				result = cursor.execute("UPDATE users set location=%s, preference=%s WHERE username=%s and is_tutor=%s", [location, option1, session['username'],True])
			except:
				flash('Update Unsuccessful', 'danger')
				return redirect(url_for('preferences_tutor'))
			#commit changes
			mysql.connection.commit()
			cursor.close() # close connection
			#use flash to define and render a response message
			flash('User Preference Successfully Updated', 'success')
			return redirect(url_for('preferences_tutor'))
		elif request.form["option"]=='Tuition at my Place':
			option2 = request.form["option"]
			app.logger.info(option2)
			cursor = mysql.connection.cursor()
			try:
				result = cursor.execute("UPDATE users set location=%s, preference=%s WHERE username=%s and is_tutor=%s", [location, option2, session['username'],True])
			except:
				flash('Update Unsuccessful', 'danger')
				return redirect(url_for('preferences_tutor'))
			#commit changes
			mysql.connection.commit()
			cursor.close() # close connection
			#use flash to define and render a response message
			flash('User Preference Successfully Updated', 'success')
			return redirect(url_for('preferences_tutor'))
		else:
			option3 = request.form["option"]
			app.logger.info(option3)
			cursor = mysql.connection.cursor()
			try:
				result = cursor.execute("UPDATE users set location=%s, preference=%s WHERE username=%s and is_tutor=%s", [location, option3, session['username'],True])
			except:
				flash('Update Unsuccessful', 'danger')
				return redirect(url_for('preferences_tutor'))
			#commit changes
			mysql.connection.commit()
			cursor.close() # close connection
			#use flash to define and render a response message
			flash('User Preference Successfully Updated', 'success')
			return redirect(url_for('preferences_tutor'))
	else:
		return render_template('tutor-student/tutor/_preferences.html')

@app.route('/tutor_upload', methods=['GET','POST'])
@is_tutor_logged_in
def upload_file_tutor():
	if request.method == 'POST':
		f = request.files['file']
		filename = secure_filename(f.filename)
		f.save(os.path.join(app.config['UPLOAD_FOLDER'],filename))
		app.logger.info(f.filename)
		flash('File Updated Successfully', 'success')
		return redirect(url_for('upload_file_student',img=f.filename))
	else:
		return render_template('tutor-student/tutor/_upload.html')

@app.route('/tutor_messages', methods=['GET','POST'])
@is_tutor_logged_in
def message_tutor():
	return render_template('tutor-student/tutor/messages.html')

@app.route('/tutor_connect', methods=['GET','POST'])
@is_tutor_logged_in
def connect_tutor():
	cursor = mysql.connection.cursor()
	result = cursor.execute("SELECT * FROM users WHERE is_student=%s", [True])
	if result > 0:
		data = cursor.fetchall()
		app.logger.info(data)
		return render_template('tutor-student/tutor/connect.html',data=data)

@app.route('/tutor_contact_form',methods=['GET','POST'])
@is_tutor_logged_in
def tutor_contact_form():
	flash('Message sent successfully','success')
	return redirect(url_for('connect_tutor'))

#Decorator to check if userlearner is logged in
def is_student_logged_in(f):
	@wraps(f)
	def wrap(*args, **kwargs):
		if 'student_logged_in' in session:
			return f(*args, **kwargs)
		else:
			flash('Unauthorized Access, Please Login','danger')
			return redirect(url_for('login_student'))
	return wrap

@app.route('/tutor_logout', methods=['GET','POST'])
@is_tutor_logged_in
def logout_tutor():
	session.clear()	# clear session
	#flash('You are logged out', 'success')
	return redirect(url_for('home'))

@app.route('/student_logout', methods=['GET','POST'])
@is_student_logged_in
def logout_student():
	session.clear()	# clear session
	#flash('You are logged out', 'success')
	return redirect(url_for('home'))


class StudentEditProfileForm(Form):
	username  = StringField('Username', validators=[InputRequired()])
	email = StringField('Email', validators=[InputRequired(),Email()])
	password = PasswordField('Password', validators=[InputRequired(), Length(min=4,max=12), EqualTo('confirm_password',message='passwords do not match')])
	confirm_password = PasswordField('Confirm Password',validators=[InputRequired(),Length(min=4,max=12)])

@app.route('/student_edit_profile',methods=['GET','POST'])
@is_student_logged_in
def edit_profile_student():
	form = StudentEditProfileForm(request.form)	#instantiate form
	if request.method == 'POST' and form.validate():
		# Get form inputs
		username = form.username.data
		email = form.email.data
		password = form.password.data

		# create cursor
		cursor = mysql.connection.cursor()

		#encrypt password entry
		encrypted_password = sha256_crypt.encrypt(str(password))
		try:
			result = cursor.execute("UPDATE users SET username = %s, email=%s, password=%s WHERE username=%s and is_student=%s", (username,email, encrypted_password, session['username'], True))
		except:
			flash('Unauthorized Username', 'danger')
			return redirect(url_for('edit_profile_student'))
		#commit changes
		mysql.connection.commit()
		cursor.close() # close connection
		#use flash to define and render a response message
		flash('User Details Successfully Updated', 'success')
		return redirect(url_for('edit_profile_student'))
		
	else:
		return render_template('tutor-student/student/edit_profile.html', form=form)

class StudentDescription(Form):
	tel = TelField('Phone Number',validators=[InputRequired()])
	description = TextAreaField('Education and Experiece', validators=[InputRequired()])
	country = StringField('Country',validators=[InputRequired()])
	language = StringField('Main Language Spoken', validators=[InputRequired()])

@app.route('/student_description', methods=['GET','POST'])
@is_student_logged_in
def description_student():
	form = StudentDescription(request.form)
	if request.method == 'POST' and form.validate():
		# Get form inputs
		tel = form.tel.data
		description = form.description.data
		country = form.country.data
		language = form.language.data
		# create cursor
		cursor = mysql.connection.cursor()
		try:
			result = cursor.execute("UPDATE users set tel=%s, description=%s, country=%s, language=%s WHERE username=%s and is_student=%s", [tel, description, country, language, session['username'],True])
		except:
			flash('Update Unsuccessful', 'danger')
			return redirect(url_for('description_student'))
		#commit changes
		mysql.connection.commit()
		cursor.close() # close connection
		#use flash to define and render a response message
		flash('User Details Successfully Updated', 'success')
		return redirect(url_for('description_student'))
	else:
		return render_template('tutor-student/student/_description.html',form=form)

@app.route('/student_preferences', methods=['GET','POST'])
@is_student_logged_in
def preferences_student():
	if request.method == 'POST':
		#get form fields
		location = request.form['location']
		app.logger.info(location)
		if request.form["option"]== 'Online Teaching':
			option1 = request.form["option"]
			app.logger.info(option1)
			cursor = mysql.connection.cursor()
			try:
				result = cursor.execute("UPDATE users set location=%s, preference=%s WHERE username=%s and is_student=%s", [location, option1, session['username'],True])
			except:
				flash('Update Unsuccessful', 'danger')
				return redirect(url_for('preferences_student'))
			#commit changes
			mysql.connection.commit()
			cursor.close() # close connection
			#use flash to define and render a response message
			flash('User Preference Successfully Updated', 'success')
			return redirect(url_for('preferences_student'))
		elif request.form["option"]=='Tuition at my Place':
			option2 = request.form["option"]
			app.logger.info(option2)
			cursor = mysql.connection.cursor()
			try:
				result = cursor.execute("UPDATE users set location=%s, preference=%s WHERE username=%s and is_student=%s", [location, option2, session['username'],True])
			except:
				flash('Update Unsuccessful', 'danger')
				return redirect(url_for('preferences_student'))
			#commit changes
			mysql.connection.commit()
			cursor.close() # close connection
			#use flash to define and render a response message
			flash('User Preference Successfully Updated', 'success')
			return redirect(url_for('preferences_student'))
		else:
			option3 = request.form["option"]
			app.logger.info(option3)
			cursor = mysql.connection.cursor()
			try:
				result = cursor.execute("UPDATE users set location=%s, preference=%s WHERE username=%s and is_student=%s", [location, option3, session['username'],True])
			except:
				flash('Update Unsuccessful', 'danger')
				return redirect(url_for('preferences_student'))
			#commit changes
			mysql.connection.commit()
			cursor.close() # close connection
			#use flash to define and render a response message
			flash('User Preference Successfully Updated', 'success')
			return redirect(url_for('preferences_student'))
	else:
		return render_template('tutor-student/student/_preferences.html')

@app.route('/student_upload', methods=['GET','POST'])
@is_student_logged_in
def upload_file_student():
	if request.method == 'POST':
		f = request.files['file']
		filename = secure_filename(f.filename)
		f.save(os.path.join(app.config['UPLOAD_FOLDER'],filename))
		app.logger.info(f.filename)
		flash('File Updated Successfully', 'success')
		return redirect(url_for('upload_file_student',img=f.filename))
	else:
		return render_template('tutor-student/student/_upload.html')


@app.route('/student_messages', methods=['GET','POST'])
@is_student_logged_in
def message_student():
	return render_template('tutor-student/student/messages.html')

@app.route('/student_connect', methods=['GET','POST'])
@is_student_logged_in
def connect_student():
	cursor = mysql.connection.cursor()
	result = cursor.execute("SELECT * FROM users WHERE is_tutor=%s", [True])
	if result > 0:
		data = cursor.fetchall()
		app.logger.info(data)
		return render_template('tutor-student/student/connect.html',data=data)

@app.route('/student_contact_form',methods=['GET','POST'])
@is_student_logged_in
def student_contact_form():
	flash('Message sent successfully','success')
	return redirect(url_for('connect_student'))

#create form register learner form field
class RegisterInstructor(Form):
	username = StringField('Username', validators=[InputRequired()])
	email = StringField('Email', validators=[InputRequired(),Email()])
	password = PasswordField('Password', validators=[InputRequired(), Length(min=4,max=12), EqualTo('confirm_password',message='passwords do not match')])
	confirm_password = PasswordField('Confirm Password',validators=[InputRequired(),Length(min=4,max=12)])

@app.route('/instructor_register', methods=['GET','POST'])
def register_instructor():
	form = RegisterInstructor(request.form)	#instantiate form
	if request.method == 'POST' and form.validate():
		# Get form inputs
		username = form.username.data
		email = form.email.data
		password = form.password.data

		# create cursor
		cursor = mysql.connection.cursor()

		#check if user exist

		q_result = cursor.execute("SELECT * FROM instructors WHERE username = %s", [username])
		if q_result > 0:
			flash('Username Unavailable','danger')
			return redirect(url_for('register_instructor'))
		else:
			#encrypt password
			encrypted_password = sha256_crypt.encrypt(str(password))
			result = cursor.execute("INSERT INTO instructors (username,email,password) VALUES (%s,%s,%s)", (username,email, encrypted_password))
			mysql.connection.commit()
			cursor.close() # close connection

			#use flash to define and render a response message
			flash('Registration Successful, Please Login', 'success')
			return redirect(url_for('login_instructor'))
		
	else:
		return render_template('instructor/register.html', form=form)

class LoginInstructor(Form):
	username = StringField('Username', validators=[InputRequired()])
	password = PasswordField('Password', validators=[InputRequired()])

@app.route('/instructor_login', methods=['GET','POST'])
def login_instructor():
	form = LoginInstructor(request.form)	#instantiate form
	if request.method == 'POST' and form.validate():
		#get inputs
		username = form.username.data
		candidate_password = form.password.data

		#create cursor
		cursor = mysql.connection.cursor()

		#check if username is valid
		result = cursor.execute("SELECT * FROM instructors WHERE username = %s", [username])
		if result > 0:
			#get password from db
			data = cursor.fetchone()
			password = data['password']
			app.logger.info(password)
			
			#compare passwords
			if sha256_crypt.verify(candidate_password, password):
				#start user session
				session['username'] = username
				session['instructor_logged_in'] = True
				#flash('You are now Logged in','success')
				return redirect(url_for('home'))
			else:
				flash('Invalid Password','danger')
				return redirect(url_for('login_instructor'))

		else:
			flash('Unknown Username','danger')
			return redirect(url_for('login_instructor'))

		#close connection
		cursor.close()
	else:
		return render_template('instructor/login.html', form=form)

#Decorator to check if userlearner is logged in
def is_instructor_logged_in(f):
	@wraps(f)
	def wrap(*args, **kwargs):
		if 'instructor_logged_in' in session:
			return f(*args, **kwargs)
		else:
			flash('Unauthorized Access, Please Login','danger')
			return redirect(url_for('login_instructor'))
	return wrap

@app.route('/instructor_logout', methods=['GET','POST'])
@is_instructor_logged_in
def logout_instructor():
	session.clear()	# clear session
	flash('You are logged out', 'success')
	return redirect(url_for('login_instructor'))

class InstructorEditProfileForm(Form):
	username  = StringField('Username', validators=[InputRequired()])
	email = StringField('Email', validators=[InputRequired(),Email()])
	password = PasswordField('Password', validators=[InputRequired(), Length(min=4,max=12), EqualTo('confirm_password',message='passwords do not match')])
	confirm_password = PasswordField('Confirm Password',validators=[InputRequired(),Length(min=4,max=12)])

@app.route('/instructor_edit_profile', methods=['GET','POST'])
@is_instructor_logged_in
def edit_profile_instructor():
	form = InstructorEditProfileForm(request.form)	#instantiate form
	if request.method == 'POST' and form.validate():
		# Get form inputs
		username = form.username.data
		email = form.email.data
		password = form.password.data

		# create cursor
		cursor = mysql.connection.cursor()

		#encrypt password entry
		encrypted_password = sha256_crypt.encrypt(str(password))
		try:
			result = cursor.execute("UPDATE instructors SET username = %s, email=%s, password=%s WHERE username=%s", (username,email, encrypted_password, session['username']))
		except:
			flash('Unauthorized Username', 'danger')
			return redirect(url_for('edit_profile_instructor'))
		#commit changes
		mysql.connection.commit()
		cursor.close() # close connection
		#use flash to define and render a response message
		flash('User Details Successfully Updated', 'success')
		return redirect(url_for('edit_profile_instructor'))
		
	else:
		return render_template('instructor/edit_profile.html', form=form)

@app.route('/instructor_messages', methods=['GET','POST'])
@is_instructor_logged_in
def message_instructor():
	return render_template('instructor/notification.html')

class InstructorCreateCourse(Form):
	course_title = StringField('Working Course Title', validators=[InputRequired()])
	course_prerequisites = StringField('Does your course have any prerequisites?', validators=[InputRequired()])
	target_student = StringField('Who is your target student?', validators=[InputRequired()])
	course_objectives = StringField('What will they learn? At the end of your course, students will be able to...', validators=[InputRequired()])

@app.route('/instructor_create_course', methods=['GET','POST'])
@is_instructor_logged_in
def create_course_instructor():
	form = InstructorCreateCourse(request.form)
	if request.method == 'POST' and form.validate():
		course_title = form.course_title.data
		course_prerequisites = form.course_prerequisites.data
		target_student = form.target_student.data
		course_objectives = form.course_objectives

		# create cursor
		cursor = mysql.connection.cursor()
		try:
			result = cursor.execute("INSERT INTO course (title,prerequisites,target_student,objectives) VALUES(%s,%s,%s,%s)", (course_title, course_prerequisites, target_student, course_objectives))
		except:
			flash('Failure in adding Response', 'danger')
			return redirect(url_for('create_course_instructor'))
		#commit changes
		mysql.connection.commit()
		cursor.close() # close connection
		#use flash to define and render a response message
		flash('Add Response SUccessfull', 'success')
		return redirect(url_for('create_course_instructor'))
	else:
		return render_template('instructor/create_course.html',form=form)

class InstructorCurriculum(Form):
	title = StringField('Title',validators=[InputRequired()])
	description = TextAreaField('Curriculum Description', validators=[InputRequired()])

@app.route('/instructor_curriculum', methods=['GET','POST'])
@is_instructor_logged_in
def curriculum_instructor():
	form = InstructorCurriculum(request.form)
	if request.method== 'POST' and form.validate():
		# create cursor
		cursor = mysql.connection.cursor()
		try:
			result = cursor.execute("INSERT INTO curriculum (title, description) VALUES(%s,%s)", (title, description))
		except:
			flash('Failure in adding Curriculum Description', 'danger')
			return redirect(url_for('curriculum_instructor'))
		#commit changes
		mysql.connection.commit()
		cursor.close() # close connection
		#use flash to define and render a response message
		flash('Successfully add curriculum Description', 'success')
		return redirect(url_for('curriculum_instructor'))
	else:
		return render_template('instructor/_curriculum.html', form=form)


if __name__ == '__main__':
	app.run(debug=True)