from flask import render_template, flash, redirect, url_for, request
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.urls import url_parse
from app import app, db
from app.forms import LoginForm, RegistrationForm, EditProfileForm, PostForm, \
ResetPasswordRequestForm, ResetPasswordForm, ContactForm
from app.models import User, Post, Votes, Memes
#from app.email import send_password_reset_email
from werkzeug.utils import secure_filename
import generate
from PIL import Image
from flask_session_captcha import FlaskSessionCaptcha
from flask import send_file
import os
import subprocess
import shlex
import tempfile
import time
from flask import make_response
from functools import wraps, update_wrapper
from datetime import datetime
import uuid

captcha = FlaskSessionCaptcha(app)


def nocache(view):
    @wraps(view)
    def no_cache(*args, **kwargs):
        response = make_response(view(*args, **kwargs))
        response.headers['Last-Modified'] = datetime.now()
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response

    return update_wrapper(no_cache, view)

@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()


@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, body=form.body.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Your campaign is now live!')
        return redirect(url_for('index'))
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.id.desc()).paginate(page, app.config['POSTS_PER_PAGE'], False)
    #posts = Post.query.join(Votes.campaign_id)paginate(page, app.config['POSTS_PER_PAGE'], False)

    next_url = url_for('index', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('index', page=posts.prev_num) \
        if posts.has_prev else None
    return render_template('index.html', title='Home', form=form,
                           posts=posts.items, next_url=next_url,
                           prev_url=prev_url)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data, mobilenumber=form.mobilenumber.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
        flash('Check your email for the instructions to reset your password')
        return redirect(url_for('login'))
    return render_template('reset_password_request.html',
                           title='Reset Password', form=form)


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been reset.')
        return redirect(url_for('login'))
    return render_template('reset_password.html', form=form)


@app.route('/user/', defaults={'username': None})
@app.route('/user/<username>')
@login_required
def user(username):
    # Handle the user looking at their own profile versus using another username
    user = None
    if not username:
        user = User.query.filter_by(username=current_user.username).first_or_404()
    else:
        user = User.query.filter_by(username=username).first_or_404()

    page = request.args.get('page', 1, type=int)
    posts = user.posts.order_by(Post.timestamp.desc()).paginate(
        page, app.config['POSTS_PER_PAGE'], False)


    # Handle the user looking at their own profile versus using another username
    next_url = None
    prev_url = None
    if not user.username == current_user.username:
        next_url = url_for('user', username=user.username, page=posts.next_num) \
            if posts.has_next else None
        prev_url = url_for('user', username=user.username, page=posts.prev_num) \
            if posts.has_prev else None
    else:
        next_url = url_for('user', page=posts.next_num) \
            if posts.has_next else None
        prev_url = url_for('user', page=posts.prev_num) \
            if posts.has_prev else None

    return render_template('user.html', user=user, current_user=current_user.username, posts=posts.items,
                           next_url=next_url, prev_url=prev_url)


@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        current_user.mobilenumber = form.mobilenumber.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
        form.mobilenumber.data = current_user.mobilenumber
    return render_template('edit_profile.html', title='Edit Profile',
                           form=form)

@app.route('/vote/<campaign_id>')
@login_required
def vote(campaign_id):

    campaign = Post.query.filter_by(id=campaign_id).first()
    v = Votes(campaign_id=campaign.id, voter_id=current_user.id)

    # Check if user has already voted
    if Votes.query.filter_by(campaign_id=campaign.id, voter_id=current_user.id).count() > 0:
        flash('You cannot vote more than once {}!'.format(current_user.username))
        return redirect(url_for('campaign', campaign_id=campaign_id))

    # User is entitled to vote so do it
    db.session.add(v)
    db.session.commit()
    # Display a thanks message and redirect
    flash('Thanks for voting {}!'.format(current_user.username))

    return redirect(url_for('campaign', campaign_id=campaign_id))

@app.route('/campaign/<campaign_id>')
@login_required
def campaign(campaign_id):
    campaign = Post.query.filter_by(id=campaign_id).first_or_404()
    canvote = True
    if Votes.query.filter_by(campaign_id=campaign.id, voter_id=current_user.id).count() > 0:
        canvote = False

    page = request.args.get('page', 1, type=int)
    memes = Memes.query.filter_by(campaign_id=campaign_id).order_by(Memes.id.desc()).paginate(
        page, app.config['POSTS_PER_PAGE'], False)

    #memes = Memes.query.join(User, (User.id == Memes.creator_id)).paginate(
    #    page, app.config['POSTS_PER_PAGE'], False)



    next_url = url_for('campaign', campaign_id=campaign_id, page=memes.next_num) \
        if memes.has_next else None
    prev_url = url_for('campaign', campaign_id=campaign_id, page=memes.prev_num) \
        if memes.has_prev else None

    return render_template('full_post.html', title='Campaign Details', post=campaign, canvote=canvote,
                           memes=memes.items, next_url=next_url, prev_url=prev_url)

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/memes/<campaign_id>/', methods=['GET', 'POST'])
@login_required
def memes(campaign_id):
    if request.method == 'POST':
        if 'image' not in request.files:
            error = "No file part"
            return render_template("error.html", context=error)
        else:
            file = request.files['image']
            if len(file.filename) < 1:
                error = "No file selected"
                return render_template("error.html", context=error)

            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filename, file_extension = os.path.splitext(filename)
                # replace file name with uuid + file_extension to ensure unique filenames
                filename = str(uuid.uuid4()) + file_extension
                ufpath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(ufpath)

                if request.form['memetext'] and len(request.form['memetext']) <= 200:
                    text = request.form.get('memetext')

                    img = Image.open(ufpath)
                    if img.height < 100 or img.width < 100:
                        img = img.resize((img.width * 4, img.height * 4))
                    elif img.height < 200 or img.width < 200:
                        img = img.resize((img.width * 2, img.height * 2))
                    img = generate.memegen(img, text)

                    # Use uuid to ensure unique filename in db
                    fname = str(uuid.uuid4()) + ".png"
                    fpath = app.config['IMAGES_FILE_NAME'].format(fname)
                    print("Filename for db {}".format(fpath))

                    img.save(fpath)
                    imgurl = url_for(
                        'static', filename='images/{}'.format(fname)
                    )
                    # Everything worked
                    # Save meme to database campaign_id, urlforimage
                    m = Memes(campaign_id=campaign_id, image_path=imgurl, creator_id=current_user.id, text=text)
                    db.session.add(m)
                    db.session.commit()

                    flash('Thanks for adding your meme !')
                    return redirect(url_for('campaign', campaign_id=campaign_id))

                else:
                    error = "Invalid input, try again"
                    return render_template("error.html", context=error)
            else:
                error = "filetype not allowed please specify a file in a png, jpg"\
                " or jpeg format"
                return render_template("error.html", context=error)
    else:
        return redirect(url_for('campaign', campaign_id=campaign_id))

@app.route('/export/<id>/', methods=['GET'])
@nocache
@login_required
def export(id):

    # cleanup folder periodically
    cleanupbanners()

    try:
        # Generate banner as HTML
        meme = Memes.query.filter_by(id=id).first_or_404()
        c = Post.query.filter_by(id=meme.campaign_id).first()

        # Read HTML from file
        leafletfile = open(os.path.join("app", "templates", "leaflet.html"), mode='r')
        html = leafletfile.read()
        leafletfile.close()

        # Replace markers with custom content. Look maw, a cheap template engine!
        html = html.replace("{{$title}}", c.title)
        html = html.replace("{{$body}}", c.body)
        html = html.replace("{{memepath}}", meme.image_path)
        html = html.replace("{{$user}}", current_user.username)

        temp = tempfile.NamedTemporaryFile(prefix=str(meme.id) + "_",
                                           suffix='.html',
                                           dir=app.config["BANNER_DIR"],
                                           delete=False)

        temp.write(bytes(html, 'UTF-8'))
        temp.close()

        shortfilename = os.path.basename(temp.name)
        shortpdffilename = os.path.splitext(shortfilename)[0] + ".pdf"
        longpdffilename = os.path.join(app.config["BANNER_DIR"], shortpdffilename)
        # Use pandoc to convert to PDF
        cmd = "/bin/bash -c \"cd " + app.config[
            "BANNER_DIR"] + " && pandoc " + shortfilename + " -o " + shortpdffilename + \
            " -M author:" + current_user.username + "\";"
        args = shlex.split(cmd)
        print(cmd)

        try:

            subprocess.check_call(args)

        except subprocess.CalledProcessError as e:
            error = "An error occurred {} ".format(str(e))
            return render_template("error.html", context=error)

    except Exception as ex:
        error = "An error occurred {} ".format(str(ex))
        return render_template("error.html", context=error)


    # force user to download the PDF
    return send_file(longpdffilename, mimetype=None, as_attachment=True, attachment_filename=longpdffilename)


@app.route('/privacy', methods=['GET'])
@app.route('/privacy/', methods=['GET'])
def privacy():
    return render_template("privacy.html")

@app.route('/about', methods=['GET'])
@app.route('/about/', methods=['GET'])
def about():
    return render_template("about.html")

@app.route('/contact', methods=['GET', 'POST'])
@app.route('/contact/', methods=['GET', 'POST'])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        flash('Thanks, but your message has gone straight into the e-shredder. Its a CTF!')
        return redirect(url_for('contact'))

    return render_template("contact.html", form=form)

@app.route('/search', methods=['GET'])
@login_required
def search():
    searchterm = request.args.get('q')
    page = request.args.get('page', 1, type=int)

    if searchterm is None or not searchterm:
        # handle blank searches
        flash('No search term provided')
        render_template("search.html")

    # handle cheap searches. Time catches up with us all!
    posts = Post.query.filter(Post.title.like("%" + searchterm +"%")).paginate(page, app.config['POSTS_PER_PAGE'], False)
    hits =  Post.query.filter(Post.title.like("%" + searchterm +"%")).count()


    next_url = url_for('search', page=posts.next_num, q=searchterm) \
    if posts.has_next else None
    prev_url = url_for('search', page=posts.prev_num, q=searchterm) \
    if posts.has_prev else None
    return render_template("search.html", searchterm=searchterm, posts=posts.items, hits=hits, next_url=next_url, prev_url=prev_url)

# Delete anything in the banners folder older than 5 minutes to keep it clean
def cleanupbanners():

    now = time.time()

    for f in os.listdir(app.config["BANNER_DIR"]):
        if os.stat(os.path.join(app.config['BANNER_DIR'], f)).st_mtime < now - (60*5):
            os.remove(os.path.join(app.config['BANNER_DIR'], f))
    return