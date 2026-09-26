from flask import Flask, render_template, make_response, request, jsonify
from flask_cors import CORS, cross_origin
from sqlalchemy.orm import Session
from sqlalchemy import and_
from models import engine, Files, GraphicsData, Languages, Education, Settlements, Dictors, Themes, Types, Subtypes
from corpora import trunc, TextGridReader, Interval, Upload
from werkzeug.utils import secure_filename
import xml.etree.ElementTree as ET
import sqlite3
import os

app = Flask(__name__, template_folder='static/templates')
CORS(app)
CORS(app, resources={r"/api/*": {"origins": "*", "allow_headers" : ['Access-Control-Allow-Origin']}})
session = Session(bind=engine)

@app.route('/')
def main_page():
    return render_template('main_page.html')

@app.route('/search', methods=['POST', 'GET'])
def search():
    languages = session.query(Languages.lang).all()
    levels = session.query(Education.name).all()
    settlements = session.query(Settlements.settlement).all()
    dictors = session.query(Dictors.name).all()
    themes = session.query(Themes.theme).all()
    types = session.query(Types.type).all()
    subtypes = session.query(Subtypes.subtype).all()
    return render_template('corpora.html', languages=languages, levels=levels, settlements=settlements, dictors=dictors, themes=themes, types=types, subtypes=subtypes)

@app.route('/results', methods=['POST', 'GET'])
def results():
    raw_results = session.query(Files.file, Files.dictor, Files.type, Files.subtype, Files.text, Files.translation, GraphicsData.pitch, GraphicsData.intensity).join(
        GraphicsData, Files.id==GraphicsData.id).all()
    tree = ET.parse('annotation.xml')
    root = tree.getroot()
    results = []
    annotations = []
    id_files = []
    for result in raw_results:
        id_files.append(result[0])
    for file in root:
        syll_bound = [0]
        syll_texts = []
        synt_bound = [0]
        synt_texts = []
        pitch_marks = []
        intens_marks = []
        if file.get('id') in id_files:
            max_time = float(file[-1].get('time'))
            for syntagm in file:
                synt_bound.append(float(syntagm.get('time')) / max_time)
                synt_texts.append(syntagm.get('text'))
                for syllabe in syntagm:
                    syll_bound.append(float(syllabe.get('time')) / max_time)
                    syll_texts.append(syllabe.text)
                    pitch_marks.append(syllabe.get('pitch'))
                    intens_marks.append(syllabe.get('intensity'))
            annotations.append([syll_bound, syll_texts, synt_bound, synt_texts, pitch_marks, intens_marks])
    for i, result in enumerate(raw_results):
        results.append(list(result) + annotations[i])
    result_page = results
    resp = make_response(render_template('results.html', result=result_page))
    return resp

@app.after_request
def set_result_headers(resp):
    resp.headers.add('Access-Control-Allow-Origin', '*')
    return resp

@app.route('/results_dialogs', methods=['POST', 'GET'])
def results_dialogs():
    results = session.query(Files.file)
    return render_template('results_dialogs.html')

@app.route('/info_barab')
def info_barab():
    return render_template('info_barab.html')

@app.route('/info_chat')
def info_chat():
    return render_template('info_chat.html')

@app.route('/info_kumand')
def info_kumand():
    return render_template('info_kumand.html')

@app.route('/info_plautdietsch')
def info_plotd():
    return render_template('info_plotd.html')

@app.route('/info_teleut')
def info_teleut():
    return render_template('info_teleut.html')

@app.route('/methods')
def methods():
    return render_template('methods.html')

@app.route('/authors')
def authors():
    return render_template('authors.html')

@app.route('/contacts')
def contacts():
    return render_template('contacts.html')

@app.route('/for_citation')
def for_citation():
    return render_template('for_citation.html')

@app.route('/authorization', methods=['GET', 'POST'])
def form_authorization():
   if request.method == 'POST':
       login = request.form.get('login')
       password = request.form.get('password')

       db = sqlite3.connect('users.db')
       cursor = db.cursor()
       cursor.execute(('''SELECT password FROM passwords
                            WHERE login = '{}';
                            ''').format(login))
       pas = cursor.fetchall()

       cursor.close()
       try:
           if pas[0][0] != password:
               return render_template('badauth.html')
       except:
           return render_template('badauth.html')

       db.close()
       return render_template('add_files.html')

   return render_template('authorization.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    upl_files = []
    files = request.files.getlist('files')
    for file in files:
        filepath = 'static/tempfiles/' + file.filename
        file.save(filepath)
        if filepath.endswith('.wav'):
            filename = filepath.removesuffix('.wav') + '.TextGrid'
            print(filename)
            upl = Upload(filename)
            upl_files.append(upl)
    for flname in os.listdir('static/tempfiles'):
        os.remove('static/tempfiles/' + flname)
    return render_template('upload.html', upl_files=upl_files)

if __name__ == '__main__':
    app.run(port=4444, debug=True)