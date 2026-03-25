from flask import render_template
from app.shared.decorators import jwt_required_html
from . import main_bp


@main_bp.route('/')
@jwt_required_html()
def index():
    return render_template('index.html')