import os
import os.path

from nltk.tag.stanford import NERTagger
import wget

from iepy.models import PreProcessSteps, Entity, EntityOccurrence
from iepy.preprocess import BasePreProcessStepRunner
from iepy.utils import DIRS, unzip_file

stanford_ner_name = 'stanford-ner-2014-01-04'
download_url_base = 'http://nlp.stanford.edu/software/'


class NonTokenizingNERTagger(NERTagger):

    @property
    def _cmd(self):
        old = super(NonTokenizingNERTagger, self)._cmd
        old = old + ["-tokenizerFactory", "edu.stanford.nlp.process.WhitespaceTokenizer"]
        return old


class NERRunner(BasePreProcessStepRunner):
    """Wrapper to insert a generic callable sentence NER tagger into the pipeline.
    """
    # TODO: rename to ner
    step = PreProcessSteps.nerc

    def __init__(self, ner, override=False):
        self.override = override
        self.ner = ner

    def __call__(self, doc):
        # this step does not necessarily requires PreProcessSteps.tagging:
        if not doc.was_preprocess_done(PreProcessSteps.sentencer):
            return
        if not self.override and doc.was_preprocess_done(PreProcessSteps.nerc):
            #print 'Already done'
            return

        entities = self.execute(doc)

        doc.set_preprocess_result(PreProcessSteps.nerc, entities)
        doc.save()

    def execute(self, doc):
        entities = []
        sent_offset = 0
        sentences = list(doc.get_sentences())  # This must be a list, it's iterated twice.
        for sent, ner_sent in zip(sentences, self.ner(sentences)):
            assert len(sent) == len(ner_sent), "Sentence length mismatch %r / %r" % (sent, ner_sent)
            i = 0
            while i < len(ner_sent):
                t, e = ner_sent[i]
                if e != 'O':
                    # entity occurrence found at position i
                    offset = i
                    # find end:
                    i += 1
                    while i < len(ner_sent) and ner_sent[i][1] == e:
                        i += 1
                    offset_end = i
                    name = ' '.join(sent[offset:offset_end])
                    kind = e.lower()  # XXX: should be in models.ENTITY_KINDS
                    entities.append(EntityOccurrence.build(name, kind, name, sent_offset + offset, sent_offset + offset_end))
                else:
                    i += 1

            sent_offset += len(sent)

        return entities


class StanfordNERRunner(NERRunner):

    def __init__(self, override=False):
        ner_path = os.path.join(DIRS.user_data_dir, stanford_ner_name)
        if not os.path.exists(ner_path):
            raise LookupError("Stanford NER not found. Try running the "
                              "command download_third_party_data.py")

        ner = NonTokenizingNERTagger(
            os.path.join(ner_path, 'classifiers', 'english.all.3class.distsim.crf.ser.gz'),
            os.path.join(ner_path, 'stanford-ner.jar'),
            encoding='utf8')

        super(StanfordNERRunner, self).__init__(ner.batch_tag, override)


def download():
    print('Downloading Stanford NER...')
    if not os.path.exists(DIRS.user_data_dir):
        os.mkdir(DIRS.user_data_dir)
    os.chdir(DIRS.user_data_dir)
    package_filename = '{0}.zip'.format(stanford_ner_name)
    zip_path = os.path.join(DIRS.user_data_dir, package_filename)
    wget.download(download_url_base + package_filename)
    unzip_file(zip_path, DIRS.user_data_dir)
