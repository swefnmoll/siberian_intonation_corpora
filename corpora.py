import mytextgrid as mtg
from sqlalchemy.orm import Session
from models import engine, Files, GraphicsData, Dictors, Types, Subtypes, FullDialogs
from sqlalchemy import desc
import xml.etree.ElementTree as ET
import parselmouth

session = Session(bind=engine)

def trunc(n):
    return int(n * 10000) / 10000

class TextGridReader():
    def __init__(self, path):
        self.tg = mtg.read_textgrid(path)
        self.path = path
        self.tiers = self.tg.tiers
        if self.read_meta_ann():
            self.accuracy = True
        else:
           self.accuracy = False

    def split_ann(self, text):
        splitted_text = text.split('//')
        splitted_ann = []
        for text in splitted_text:
            splitted_ann.append(text.strip())
        return splitted_ann

    def read_meta_ann(self):
        for interval in self.tiers[0]:
            if interval.text:
                self.meta_ann = interval.text
                break
        try:
            self.text, self.transl, self.dictor, self.type, self.subtype = self.split_ann(self.meta_ann)
        except:
            return False
        return True

class Interval():
    def __init__(self, path, snd, tier=0, text=None, parent=None):
        self.tier = tier
        self.parent = parent
        self.tg = mtg.read_textgrid(path)
        self.snd = snd
        self.chars = {'max_pitch' : None, 'min_pitch' : None, 'max_intens' : None, 'min_intens' : None}
        self.boundary = trunc(snd.xmax)
        self.text = text
        self.intervals = []
        if tier != 2:
            for interval in self.tg.tiers[tier + 1]:
                if trunc(interval.xmin) >= trunc(snd.xmin) and trunc(interval.xmax) <= trunc(snd.xmax):
                    self.intervals.append(Interval(
                        path, snd.extract_part(from_time=interval.xmin, to_time=interval.xmax, preserve_times=True), tier + 1, text=interval.text, parent=self))
        self.get_chars()

    def get_chars(self):
        try:
            self.raw_pitch = self.snd.to_pitch_ac(pitch_floor=50, pitch_ceiling=800, silence_threshold=0.09, voicing_threshold=0.45, octave_cost=0.055).selected_array['frequency']
        except:
            self.raw_pitch = [0]
        self.pitch = []
        self.pitch_for_graph = []
        for point in self.raw_pitch:
            self.pitch_for_graph.append(int(point))
            if point != 0:
                self.pitch.append(int(point))
        try:
            self.raw_intensity = self.snd.to_intensity().values.T
        except:
            self.raw_intensity = [[0]]
        self.intensity = []
        for point in self.raw_intensity:
            self.intensity.append(int(point[0]))
        if len(self.pitch) == 0:
            self.pitch = [0]
        if len(self.intensity) == 0:
            self.intensity = [0]
        self.chars['max_pitch'] = int(max(self.pitch))
        self.chars['min_pitch'] = int(min(self.pitch))
        self.chars['max_intens'] = int(max(self.intensity))
        self.chars['min_intens'] = int(min(self.intensity))

    def __iter__(self):
        return iter(self.intervals)

    def __enter__(self):
        return self
    
    def __exit__(self, type, value, tb):
        pass

    def pitch_mark(self):
        pitch_mark = 'N'
        with self.parent as syntagm, self.parent.parent as sentence:    
            if self.chars['max_pitch'] == syntagm.chars['max_pitch']:
                pitch_mark = 'H'
            elif self.chars['min_pitch'] == syntagm.chars['min_pitch'] and self.chars['max_pitch'] != syntagm.chars['max_pitch']:
                pitch_mark = 'L'
            elif self.chars['min_pitch'] == syntagm.chars['min_pitch'] and self.chars['max_pitch'] == syntagm.chars['max_pitch']:
                pitch_mark = 'L/H'
            if self.chars['max_pitch'] == sentence.chars['max_pitch'] or self.chars['min_pitch'] == sentence.chars['min_pitch']:
                pitch_mark += '!'
            return pitch_mark

    def intens_mark(self):
        intens_mark = 'N'
        with self.parent as syntagm, self.parent.parent as sentence:    
            if self.chars['max_intens'] == syntagm.chars['max_intens']:
                intens_mark = 'H'
            elif self.chars['min_intens'] == syntagm.chars['min_intens'] and self.chars['max_intens'] != sentence.chars['max_intens']:
                intens_mark = 'L'
            elif self.chars['min_intens'] == syntagm.chars['min_intens'] and self.chars['max_intens'] == sentence.chars['max_intens']:
                intens_mark = 'L/H'
            if self.chars['max_intens'] == sentence.chars['max_intens'] or self.chars['min_intens'] == sentence.chars['min_intens']:
                intens_mark += '!'
        return intens_mark        

class Upload():
    def __init__(self, path):
        snd = parselmouth.Sound(path.removesuffix('.TextGrid') + '.wav')
        self.metadata = TextGridReader(path)
        self.file = Interval(path, snd)
        self.id = get_id(Files)
        if not self.metadata.accuracy:
            self.upl_str = 'Не удалось загрузить файл ' + path + '! Пожалуйста, перепроверьте наличие всех пунктов в метаразметке, а также - наличие двойных косых черт.'
            return None
        if not self.upload_metadata():
            self.upl_str = 'Не удалось загрузить файл ' + path + '! Пожалуйста, перепроверьте метаразметку.'
            return None
        self.upload_data()
        self.upload_graphics_data()
        snd.save('static/audio/' + str(self.id)  + '.wav', 'WAV')
        self.upl_str = 'Загружен файл ' + path

    def __str__(self):
        return self.upl_str
    
    def upload_data(self):
        tree = ET.parse('annotation.xml')
        root = tree.getroot()
        file = ET.SubElement(root, 'file')
        file.set('id', str(self.id))
        for syntagm in self.file:
            synt = ET.SubElement(file, 'syntagm')
            synt.set('time', str(syntagm.boundary))
            synt.set('text', syntagm.text)
            for syllabe in syntagm:
                syll = ET.SubElement(synt, 'syllabe')
                syll.set('time', str(syllabe.boundary))
                syll.set('pitch', str(syllabe.pitch_mark()))
                syll.set('intensity', str(syllabe.intens_mark()))
                syll.text = syllabe.text
        ET.indent(root)
        tree.write('annotation.xml', encoding='utf-8', xml_declaration=True) 
        
    def upload_metadata(self):
        dictor_id = self.get_dictor_id(self.metadata.dictor)
        type_id = self.get_type_id(self.metadata.type)
        subtype_id = self.get_subtype_id(self.metadata.subtype)
        if not(dictor_id and type_id and subtype_id):
            return False
        file = Files(
            dictor = dictor_id,
            type = type_id,
            subtype = subtype_id,
            text = self.metadata.text,
            translation = self.metadata.transl
            )
        session.add(file)
        session.commit()
        return True

    def get_dictor_id(self, name):
        try:
            return session.query(Dictors.id).filter(Dictors.name == name).one()[0]
        except:
            return False

    def get_type_id(self, type):
        try:
            return session.query(Types.id).filter(Types.type.like(f'{type[0:2]}%')).one()[0]
        except:
            return False

    def get_subtype_id(self, subtype):
        try:
            return session.query(Subtypes.id).filter(Subtypes.subtype.like(f'{subtype[0:2]}%')).one()[0]
        except:
            return False
    
    def upload_graphics_data(self):
        graphic = GraphicsData(
            pitch = str(self.file.pitch_for_graph),
            intensity = str(self.file.intensity)
        )
        session.add(graphic)
        session.commit()

class UploadDialog():
    def __init__(self, wav_file, text_file, transl_file, theme, first_dictor, second_dictor, lang):
        self.id = get_id(FullDialogs)
        wav_file.save('static/full_dialogs/wav/' + str(self.id))
        text_file.save('static/full_dialogs/texts/' + str(self.id))
        transl_file.save('static/full_dialogs/translations/' + str(self.id))
        dialog = FullDialogs(
            lang = lang,
            theme = theme,
            dictor1 = first_dictor,
            dictor2 = second_dictor
            )
        session.add(dialog)
        session.commit()

    def __str__(self):
        return 'Диалог успешно загружен'


def get_id(table):
    last_id = session.query(table.id).order_by(table.id.desc()).first()
    if not last_id:
        return 1
    else:
        return last_id[0] + 1
