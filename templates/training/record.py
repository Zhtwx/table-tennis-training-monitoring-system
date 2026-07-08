from flask import Blueprint, render_template, request, jsonify

training_bp = Blueprint('training', __name__, url_prefix='/training')

# 已有的路由
@training_bp.route('/batch_import', methods=['GET', 'POST'])
def batch_import():
    return render_template('batch_import.html')


# 👇 在文件末尾加上这个
@training_bp.route('/training_record')
def training_record():
    return render_template('training_record.html')