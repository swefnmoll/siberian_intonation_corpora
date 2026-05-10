from flask import Flask, render_template, make_response
from flask_cors import CORS, cross_origin
from sqlalchemy.orm import Session
from sqlalchemy import and_
from models import engine, Files, GraphicsData, Languages, Education, Settlements, Dictors, Themes, Types, Subtypes
import xml.etree.ElementTree as ET

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
    results = session.query(Files.file, Files.dictor, Files.type, Files.subtype, Files.text, Files.translation, GraphicsData.pitch, GraphicsData.intensity).join(
        GraphicsData, Files.id==GraphicsData.id).all()
    print(results)
    syll_boundaries = []
    syll_texts = []
    synt_boundaries = []
    synt_texts = []
    tree = ET.parse('annotation.xml')
    root = tree.getroot()
    for file in root:
        if file.get('id') in results[0]:
            max_time = file[-1].get('time')
            for syntagm in file:
                synt_boundaries.append(syntagm.get('time') / max_time)
                synt_texts.append(syntagm.text)
                for syllabe in syntagm:
                    syll_boundaries.append(syllabe.get('time') / max_time)
                    syll_texts.append(syllabe.text)
    resp = make_response(render_template('results.html', result=results, syll_boundaries=syll_boundaries, syll_texts=syll_texts))
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


if __name__ == '__main__':
    app.run(port=4444, debug=True)