from flask import Flask, render_template, make_response, request, jsonify
from flask_cors import CORS, cross_origin
from sqlalchemy.orm import Session, aliased
from sqlalchemy import and_
from models import engine, Files, GraphicsData, Languages, Education, Settlements, Dictors, Themes, Types, Subtypes, FullDialogs
from corpora import trunc, TextGridReader, Interval, Upload
from werkzeug.utils import secure_filename
from flask_paginate import Pagination, get_page_parameter
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
    lang_rows = session.query(Languages.lang).all()
    languages = []
    for lang in lang_rows:
        languages.append(lang[0])
    levels_rows = session.query(Education.name).all()
    levels = []
    for level in levels_rows:
        levels.append(level[0])
    settlements_rows = session.query(Settlements.settlement).all()
    settlements = []
    for settlement in settlements_rows:
        settlements.append(settlement[0])
    dictors_rows = session.query(Dictors.name).all()
    dictors = []
    for dictor in dictors_rows:
        dictors.append(dictor[0])
    themes_rows = session.query(Themes.theme).all()
    themes = []
    for theme in themes_rows:
        themes.append(theme[0]) 
    types_rows = session.query(Types.type).all()
    types = []
    for type in types_rows:
        types.append(type[0])    
    subtypes_rows = session.query(Subtypes.subtype).all()
    subtypes = []
    for subtype in subtypes_rows:
        subtypes.append(subtype[0])    
    return render_template('corpora.html', languages=languages, levels=levels, settlements=settlements, dictors=dictors, themes=themes, types=types, subtypes=subtypes)

@app.route('/results', methods=['POST', 'GET'])
def results():
    per_page = 10
    page = request.args.get(get_page_parameter(), type=int, default=1)
    offset = (page - 1) * per_page
    query = session.query(Files.id, Dictors.name, Types.type, Subtypes.subtype, Files.text, Files.translation, GraphicsData.pitch, GraphicsData.intensity).join(
        GraphicsData, Files.id==GraphicsData.id).join(
            Dictors, Files.dictor==Dictors.id).join(
                Types, Files.type == Types.type
                ).join(
                Subtypes, Files.subtype == Subtypes.subtype
                ).filter(and_(
            Files.type.like(f'{request.args.get('type')}%'),
            Files.subtype.like(f'{request.args.get('subtype')}%'),
            Dictors.name.like(f'{request.args.get('dictor')}%'),
            Dictors.lang.like(f'{request.args.get('lang')}%'),
            Dictors.education.like(f'{request.args.get('education')}%'),
            Dictors.settlement.like(f'{request.args.get('settlement')}%'),
            Dictors.gender.like(f'{request.args.get('gender')}%'),
            Dictors.dob >= request.args.get('dob').split(',')[0],
            Dictors.dob <= request.args.get('dob').split(',')[1]
        ))
    total = len(query.all())
    raw_results = query.offset(offset).limit(per_page).all()
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
        if int(file.get('id')) in id_files:
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
    pagination = Pagination(page=page, page_per=per_page, total=total, offset=offset, prev_label='<', next_label='>', bs_version=5)
    resp = make_response(render_template('results.html', result=results, pagination=pagination, css_framework='bootstrap5'))
    return resp

@app.after_request
def set_result_headers(resp):
    resp.headers.add('Access-Control-Allow-Origin', '*')
    return resp

@app.route('/results_dialogs', methods=['POST', 'GET'])
def results_dialogs():
    per_page = 10
    page = request.args.get(get_page_parameter(), type=int, default=1)
    offset = (page - 1) * per_page
    dictors_alias = aliased(Dictors)
    query = session.query(FullDialogs.id, Languages.lang, Themes.theme, Dictors.name, dictors_alias.name).join(
        Languages, FullDialogs.lang == Languages.id).join(
            Themes, FullDialogs.theme == Themes.id).join(
                Dictors, FullDialogs.dictor1 == Dictors.id).join(
                    dictors_alias, FullDialogs.dictor2 == dictors_alias.id).filter(and_(
                        Themes.theme.like(f'{request.args.get('theme')}%'),
                        Languages.lang.like(f'{request.args.get('lang')}%')))
    total = len(query.all())
    raw_results = query.offset(offset).limit(per_page).all()

    def read_text_and_tranls(id):
        with open(f'static/full_dialogs/texts/{id}.txt', 'r', encoding='utf-8') as file:
            text = file.read().splitlines()
        with open(f'static/full_dialogs/translations/{id}.txt', 'r', encoding='utf-8') as file:
            transl = file.read().splitlines()
        return text, transl
    
    results = []
    
    for result in raw_results:
        id = int(result[0])
        results.append(list(result) + list(read_text_and_tranls(id)))

    pagination = Pagination(page=page, page_per=per_page, total=total, offset=offset, prev_label='<', next_label='>', bs_version=5)
    return render_template('results_dialogs.html', result=results, pagination=pagination, css_framework='bootstrap5')

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
    session.close()
    return render_template('upload.html', upl_files=upl_files)

if __name__ == '__main__':
    app.run(port=4444, debug=True)