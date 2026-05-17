import os

from sqlalchemy.pool import StaticPool

basedir = os.path.abspath(os.path.dirname(__file__))
default_db_path = 'sqlite:///' + os.path.join(basedir, 'mycal.db')

class Config:
  SQLALCHEMY_DATABASE_URI = os.environ.get('MYCAL_DATABASE_URL') or default_db_path
  SQLALCHEMY_TRACK_MODIFICATIONS = False

  SECRET_KEY = os.environ.get('MYCAL_SECRET_KEY') or 'dev-secret-key-change-before-deployment'

class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

class DeploymentConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or default_db_path
