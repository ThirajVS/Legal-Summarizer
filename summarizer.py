from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lex_rank import LexRankSummarizer
from sumy.summarizers.text_rank import TextRankSummarizer
from sumy.summarizers.lsa import LsaSummarizer
from sumy.nlp.stemmers import Stemmer
from sumy.utils import get_stop_words

class Summarizer:
    def __init__(self):
        self.language = "english"
        stemmer = Stemmer(self.language)
        self.models = {
            "lexrank": LexRankSummarizer(stemmer),
            "textrank": TextRankSummarizer(stemmer),
            "lsa": LsaSummarizer(stemmer),
        }
        for model in self.models.values():
            model.stop_words = get_stop_words(self.language)

    def _clean(self, text: str) -> str:
        return " ".join((text or "").replace("\r", " ").replace("\t", " ").split())

    def summarize(self, text: str, sentences_count: int = 6) -> str:
        text = self._clean(text)
        if not text:
            return "No content to summarize."
        parser = PlaintextParser.from_string(text, Tokenizer(self.language))
        outputs = []
        for model in self.models.values():
            try:
                sents = [str(s) for s in model(parser.document, sentences_count)]
                chunk = " ".join(sents).strip()
                if chunk:
                    outputs.append(chunk)
            except Exception:
                pass
        if not outputs:
            first = " ".join([str(s) for s in parser.document.sentences[:sentences_count]])
            return first[:2000] if first else text[:2000]
        combined = " ".join(outputs[:2]) if len(outputs) >= 2 else outputs[0]
        return combined[:2000]

def summarize_text(text: str) -> str:
    return Summarizer().summarize(text)
