from app import create_app, db
from app.config import DeploymentConfig

app = create_app(DeploymentConfig)

if __name__ == '__main__':
    app.run()