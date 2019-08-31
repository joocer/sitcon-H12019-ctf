import os
basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'NeverGonnaGiveYouUp'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    ADMINS = ['your-email@example.com']
    POSTS_PER_PAGE = 5
    CAPTCHA_ENABLE = True
    CAPTCHA_NUMERIC_DIGITS = 5
    SESSION_TYPE = 'filesystem'
    BANNER_DIR = os.path.join(basedir, 'app', 'banners')
    UPLOAD_FOLDER = os.path.join("app", "static", "upload")
    IMAGES_FOLDER = os.path.join("app", "static", "images")
    IMAGES_FILE_NAME = 'app/static/images/{}'
    ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    WTF_CSRF_METHODS = []  # Disable CSRF
