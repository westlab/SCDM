from flask import Blueprint

v1 = Blueprint('v1', __name__)

@v1.route("/test")
def test():
    return "hellow from api.py"


