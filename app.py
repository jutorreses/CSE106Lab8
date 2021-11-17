# importing the necessary modules
from flask import Flask, render_template, request, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
import datetime

# initialize the app
app = Flask(__name__)

# config the sqlalchemy
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///student_enrollment.db'
app.config['SECRET_KEY'] = 'mysecret'

db = SQLAlchemy(app)

# create user model for databases
class Users(db.Model):
    # define the necessary fields for the users database
    id = db.Column(db.Integer, primary_key = True, autoincrement=True)
    username = db.Column(db.String(30), unique=True)
    password = db.Column(db.String(30))
    teachers = db.relationship("Teachers", backref="teacher_user_id")
    students = db.relationship("Students", backref="students_user_id")

# define the students model for databases
class Students(db.Model):
    # define the neccessary field for student database
    id = db.Column(db.Integer, primary_key = True, autoincrement=True)
    name = db.Column(db.String(30))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    enrollment = db.relationship("Enrollment", backref="student_user_id")

# define the teachers model for databases
class Teachers(db.Model):
    # define the neccessary field for teachers database
    id = db.Column(db.Integer, primary_key = True, autoincrement=True)
    name = db.Column(db.String(30))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    classes = db.relationship("Classes", backref="teacher_user_id")

# define the Class model for database
class Classes(db.Model):
    # define the neccessary field for classes database
    id = db.Column(db.Integer, primary_key = True, autoincrement=True)
    course_name = db.Column(db.String(30))
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'))
    number_enrolled = db.Column(db.Integer)
    capacity = db.Column(db.Integer)
    start = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    end = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    enrollment = db.relationship("Enrollment", backref="class_enrollment_id")

# define the enrollment model for database
class Enrollment(db.Model):
    # define the neccessary field for enrollment database
    id = db.Column(db.Integer, primary_key = True, autoincrement=True)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"))
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"))
    grade = db.Column(db.String(10))


# define a route for index page
@app.route('/', methods=['GET'])
def index():
    if len(session) > 0:            # if user already logged in go to the index page
        user_id = session['id']
        teacher = Teachers.query.filter(Teachers.user_id == user_id).first()
        student = Students.query.filter(Students.user_id == user_id).first()
        if teacher:   # if user is a teacher 
            # get all course teached by teacher
            classes = Classes.query.filter(Classes.teacher_id == teacher.id).all()
            my_course_data = []
            for course in classes:
                teacher = Teachers.query.filter(course.teacher_id == Teachers.id).first()
                dic = {"class_id": course.id, "course name": course.course_name, "teacher": teacher.name, "start": course.start, "end": course.end, "students enrolled": course.number_enrolled, "capacity": course.capacity }
                my_course_data.append(dic)
            return render_template("index.html", data=my_course_data, teacher=teacher.name)
        else:        # if user is a student

            # get all enrollment courses enrolled by the student
            enrollment = Enrollment.query.filter(Enrollment.student_id == student.id).all()

            my_course_data = []
            course_data = []
            enrolled_courses = []
            # loop over the enrollment details
            for enroll in enrollment:
                classes = Classes.query.filter(Classes.id == enroll.class_id).first()
                teacher = Teachers.query.filter(Teachers.id == classes.teacher_id).first()
                dic = {"student": student.name, "course name": classes.course_name, "teacher": teacher.name, "start": classes.start, "end": classes.end, "students enrolled": classes.number_enrolled, "capacity": classes.capacity, }
                my_course_data.append(dic)
                enrolled_courses.append(classes.course_name)

            courses = Classes.query.all()
            # loop through the courses details
            for course in courses:
                enrolled = False
                teacher = Teachers.query.filter(Teachers.id == course.teacher_id).first()
                if course.course_name in enrolled_courses:
                    enrolled = True
                c = {"student_id": student.id, "class_id": course.id, "course name": course.course_name, "teacher": teacher.name, "start": course.start, "end": course.end, "students enrolled": course.number_enrolled, "enrolled": enrolled, "capacity": course.capacity}
                course_data.append(c)
            
            # rendering the index.html template
            return render_template("index.html", data=my_course_data, courses=course_data, student=student.name)
    else:
        # if no user exits in session then go the login page
        return redirect(url_for('login'))

# define route for the enroll student
@app.route("/enroll/<int:student_id>/<int:class_id>", methods = ['GET'])
def enroll(student_id, class_id):
    # create new enrollment
    enrollment = Enrollment(class_id = class_id, student_id = student_id, grade = 0)
    # get enrolled students
    enrolled_student = Enrollment.query.filter(Enrollment.class_id == class_id).all()
    classes = Classes.query.filter(Classes.id == class_id).first()
    # check the capacity of classes
    if classes.number_enrolled >= classes.capacity:
        return redirect(url_for("index"))

    # update the enrolled student count 
    classes.number_enrolled = len(enrolled_student) + 1

    # commit the changes in the database
    db.session.add(classes)
    db.session.add(enrollment)
    db.session.commit()
    # finally redirect to the index page
    return redirect(url_for('index'))

# define a route to handle for unenroll the student from the course
@app.route("/unenroll/<int:student_id>/<int:class_id>", methods = ['GET'])
def unenroll(student_id, class_id):
    enrollment = Enrollment.query.filter(Enrollment.class_id == class_id, Enrollment.student_id == student_id).delete()
    enrolled_student = Enrollment.query.filter(Enrollment.class_id == class_id).all()
    classes = Classes.query.filter(Classes.id == class_id).first()
    classes.number_enrolled = len(enrolled_student)
    db.session.add(classes) 
    db.session.commit()
    return redirect(url_for('index'))

# get the course details of the particular course
@app.route("/course_details/<int:class_id>", methods=['GET'])
def course_details(class_id):
    # get the enrolled student from the course id
    enrolled_students = Enrollment.query.filter(Enrollment.class_id == class_id).all()
    data = []
    # loop over the enrolled students in the course
    for enroll in enrolled_students:
        # get the student enrolled in the couse
        student = Students.query.filter(Students.id == enroll.student_id).first()
        dic = {"class id":class_id, "student id": student.id, "student name": student.name, "grade": enroll.grade}
        # append the neccessary data to final list 
        data.append(dic)
    # rendering the course_details tempates 
    return render_template("course_details.html", data=data)

# define a to edit the grade of student
@app.route('/edit_grade/<int:student_id>/<int:class_id>', methods=['GET', 'POST'])
def edit_grade(student_id, class_id):
    if request.method == 'GET':
        # get the enrolled student from the course
        enrolled_students = Enrollment.query.filter(Enrollment.student_id == student_id, Enrollment.class_id == class_id).first()
        grade = {"grades": enrolled_students.grade, "student_id": student_id, "class_id": class_id}
        # rendering the template to screen with that enrolled student data
        return render_template("edit_grades.html", data=grade)
    
    if request.method == 'POST':
        # get the enrolled student from the course
        enrolled_students = Enrollment.query.filter(Enrollment.student_id == student_id, Enrollment.class_id == class_id).first()
        # update the grade 
        grade = request.form['grade']
        enrolled_students.grade = grade
        # add the updated grade to the database
        db.session.add(enrolled_students) 
        db.session.commit()
        # redirect to the course details page
        return redirect(url_for("course_details", class_id = enrolled_students.class_id))

# define a route for login 
@app.route('/login', methods =['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        # get the form data
        username = request.form['username']
        password = request.form['password']

        # get username and password and compare it with the username and password present in the database
        user = Users.query.filter(Users.username==username, Users.password==password).first()
        if user:
            # set the session 
            session['loggedin'] = True
            session['id'] = user.id
            session['username'] = user.username
            msg = 'Logged in successfully !'
            # redirect to the index page
            return redirect(url_for('index'))
        else:
            # if user doesnot render login page with 'Incorrect username / password !' message
            msg = 'Incorrect username / password !'
    return render_template('login.html', msg = msg)
  
# define a route for logout
@app.route('/logout')
def logout():
    # pop out all the data form the session
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    # redirect to the login page
    return redirect(url_for('login'))

# register flask-admin with app
admin = Admin(app)
# create a view of flask-admin according to the database
admin.add_view(ModelView(Users, db.session))
admin.add_view(ModelView(Teachers, db.session))
admin.add_view(ModelView(Students, db.session))
admin.add_view(ModelView(Classes, db.session))
admin.add_view(ModelView(Enrollment, db.session))

# start the app with debugging mode
if __name__ == '__main__':
    app.run(debug=True)