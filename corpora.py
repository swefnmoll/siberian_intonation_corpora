import mytextgrid as mtg
from sqlalchemy.orm import Session
from models import engine, Files
import xml.etree.ElementTree as ET
import parselmouth

session = Session(bind=engine)

class Syntagm():
    def __init__(self, text, left_boundary, right_boundary, syllabes, snd):
        self.text = text
        self.syllabes = []
        self.max_pitch, self.min_pitch, self.max_intens, self.min_intens = None
        self.boundary = right_boundary
        for syllabe in syllabes:
            if syllabe.xmin >= left_boundary and syllabe.xmax <= right_boundary:
                self.syllabes.append(Syllabe(syllabe.text, syllabe.xmax, snd))
            elif syllabe.xmin >= right_boundary:
                break

class Syllabe():
    def __init__(self, text, left_boundary, right_boundary, snd):
        self.text = text
        self.max_pitch, self.min_pitch, self.max_intens, self.min_intens = None
        self.left_boundary = left_boundary
        self.right_boundary = right_boundary
        self.sound = None
        self.mark = None

    def __eq__(self, other):
        return self.boundary == other.boundary

    def get_chars(self):
        pitch = self.sound.to_pitch_ac(
            pitch_floor=50, pitch_ceiling=800, silence_threshold=0.09,
            voicing_threshold=0.45, octave_cost=0.055).selected_array['frequency']
        intensity = self.sound.to_intensity().values.T
        self.max_pitch = max(pitch)
        self.min_pitch = min(pitch)
        self.max_intens = max(intensity)
        self.min_intens = min(intensity)

class TextGrid():
    def __init__(self, path):
        self.tg = mtg.read_textgrid(path)
        self.meta_tier = self.tg.tiers[0]
        self.syntagm_tier = self.tg.tiers[1]
        self.syllable_tier = self.tg.tiers[2]
        self.read_meta_ann(path)
        self.read_ann()
        self.new_filename = self.get_filename()

    def split_ann(self, text):
        splitted_text = text.split('//')
        return splitted_text

    def read_meta_ann(self, path):
        for interval in self.meta_tier:
            if interval.text:
                self.meta_ann = interval.text
                break
        try:
            self.text, self.transl, self.dictor, self.type, self.subtype = self.split_ann(self.meta_ann)
        except TypeError:
            return 'Некорректная разметка первого уровня в файле ' + path + '. Пожалуйста, перепроверьте файл.'

    def read_ann(self):
        self.syntagmas = []
        for interval in self.syntagm_tier:
            self.syntagmas.append(Syntagm(interval.text, interval.xmin, interval.xmax, self.syllabe_tier, self.snd))

    def get_filename(self):
        id = session.query(Files).filter(Files.dictor == self.dictor).count() + 1
        return self.dictor + '_' + str(id)


#class User():


class Annotation():
    def __init__(self, path, textgr):
        self.snd = parselmouth.Sound(path)
        self.read_pitch()
        self.read_intensity()
        self.annotate_syntagmas(textgr)
        self.annotate_sentence(textgr)

    def read_pitch(self):
        self.raw_pitch = self.snd.to_pitch_ac(
            pitch_floor=50, pitch_ceiling=800, silence_threshold=0.09,
            voicing_threshold=0.45, octave_cost=0.055).selected_array['frequency']
        self.pitch = list(filter(lambda x: x != 0, self.raw_pitch))

    def read_intensity(self):
        self.intensity = self.snd.to_intensity()
        self.intensity_values = self.intensity.values.T

    def annotate_syntagmas(self, textgr):
        self.abs_max_pitch, self.abs_min_pitch, self.abs_max_intens, self.abs_min_intens = None
        for syntagm in textgr.syntagmas:
            for syllabe in syntagm:
                syllabe.sound = self.snd.extract_part(from_time=syllabe.left_boundary,
                                                      to_time=syllabe.right_boundary,
                                                      preserve_times=True)
                syllabe.get_chars()
                if not syntagm.max_pitch:
                    syntagm.max_pitch = syllabe.max_pitch
                    syntagm.min_pitch = syllabe.min_pitch
                    syntagm.max_intens = syllabe.max_intens
                    syntagm.min_intens = syllabe.min_intens
                else:
                    if syntagm.max_pitch > syllabe.max_pitch:
                        syntagm.max_pitch = syllabe.max_pitch
                    if syntagm.min_pitch < syllabe.min_pitch:
                        syntagm.min_pitch = syllabe.min_pitch
                    if syntagm.max_intens > syllabe.max_intens:
                        syntagm.max_intens = syllabe.max_intens
                    if syntagm.min_intens < syllabe.min_intens:
                        syntagm.min_intens = syllabe.min_intens
            if not self.abs_max_pitch:
                self.abs_max_pitch = syntagm.max_pitch
                self.abs_min_pitch = syntagm.min_pitch
                self.abs_max_intens = syntagm.max_intens
                self.abs_min_intens = syntagm.min_intens
            else:
                if self.abs_max_pitch > syntagm.max_pitch:
                    self.abs_max_pitch = syntagm.max_pitch
                if self.abs_min_pitch < syntagm.min_pitch:
                    self.abs_min_pitch = syntagm.min_pitch
                if self.abs_max_intens > syntagm.max_intens:
                    self.abs_max_intens = syntagm.max_intens
                if self.abs_min_intens < syntagm.min_intens:
                    self.abs_min_intens = syntagm.min_intens

    def write_ann(self):
        tree = ET.parse('annotation.xml')        
        root = tree.getroot()
        
        
        ET.indent(root)
        tree.write('annotation.xml', encoding='utf-8', xml_declaration=True)
        
# G:\Мой диск\Интонационная БД\Барабинцы\Звуковые файлы по высказываниям\Загружено\ААР_модал_2.TextGrid
# raw_pitch = snd.to_pitch_ac(pitch_floor=50, pitch_ceiling=800, silence_threshold=0.09, voicing_threshold=0.45, octave_cost=0.055).selected_array['frequency']
class Upload():
    def __init__(self, path):
        self.textgr = TextGrid(path)
        self.upload_data(path)
        self.upload_metadata(path)
        ann = Annotation(path, self.textgr)

    def upload_data(self, path):
        tree = ET.parse('annotation.xml')
        root = tree.getroot()
        file = ET.SubElement(root, 'file')
        file.set('id', self.textgr.new_filename)
        for syntagm in self.textgr.syntagmas:
            synt = ET.SubElement(file, 'syntagm')
            synt.set('time', str(syntagm.boundary))
            synt.text = syntagm.text
            for syllabe in syntagm:
                syll = ET.SubElement(synt, 'syllabe')
                syll.set('time', str(syllabe.right_boundary))
                syll.text = syllabe.text
            
        ET.indent(root)
        tree.write('annotation.xml', encoding='utf-8', xml_declaration=True) 
        
    def upload_metadata(self, path):
        file = Files(
            file = path.removesuffix('.TextGrid'),
            dictor = self.textgr.dictor,
            type = self.textgr.type,
            subtype = self.textgr.subtype,
            text = self.textgr.text,
            translation = self.textgr.transl
            )
        
path = input('Имя файла: ')
upl = Upload(path)