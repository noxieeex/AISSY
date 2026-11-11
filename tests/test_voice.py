from types import SimpleNamespace

import pytest

np = pytest.importorskip("numpy")

from aissy.voice import (
    Pyttsx3Speaker,
    SAMPLE_RATE,
    VoiceSession,
    WhisperTranscriber,
    clean_for_speech,
    is_silent,
    pick_voice,
)


# ---------- limpeza do texto ----------

def test_clean_removes_emoji_markdown_and_ids():
    text = "**Anotado!** 💗 Tarefa #3: `Estudar`\n- ok <3"

    cleaned = clean_for_speech(text)

    assert "💗" not in cleaned and "*" not in cleaned and "`" not in cleaned
    assert "<3" not in cleaned
    assert "número 3" in cleaned
    assert "\n" not in cleaned


def test_clean_removes_links():
    assert "http" not in clean_for_speech("veja https://exemplo.com agora")


def test_clean_empty_when_only_symbols():
    assert clean_for_speech("💗 💗") == ""


# ---------- silêncio ----------

def test_short_audio_is_silent():
    assert is_silent(np.ones(100, dtype="float32")) is True


def test_quiet_audio_is_silent():
    assert is_silent(np.zeros(SAMPLE_RATE * 2, dtype="float32")) is True


def test_speech_level_audio_is_not_silent():
    t = np.linspace(0, 2, SAMPLE_RATE * 2, dtype="float32")
    audio = 0.3 * np.sin(2 * np.pi * 220 * t)

    assert is_silent(audio) is False


def test_transcriber_skips_model_on_silence():
    transcriber = WhisperTranscriber()

    # Se tentasse carregar o modelo, o import falharia ou demoraria.
    assert transcriber.transcribe(np.zeros(10, dtype="float32")) == ""
    assert transcriber._model is None


# ---------- escolha de voz ----------

VOICES = [
    SimpleNamespace(id="HKEY\\TTS_MS_EN-US_ZIRA_11.0", name="Microsoft Zira"),
    SimpleNamespace(id="HKEY\\TTS_MS_PT-BR_MARIA_11.0", name="Microsoft Maria"),
    SimpleNamespace(id="HKEY\\TTS_MS_ES-ES_HELENA_11.0", name="Microsoft Helena"),
]


@pytest.mark.parametrize(
    "language, expected",
    [("pt-BR", "Maria"), ("en", "Zira"), ("es", "Helena")],
)
def test_pick_voice_by_language(language, expected):
    assert expected in pick_voice(VOICES, language).name


def test_pick_voice_prefers_female_over_male_in_same_language():
    voices = [
        SimpleNamespace(id="TTS_MS_PT-BR_DANIEL_11.0", name="Microsoft Daniel"),
        SimpleNamespace(id="TTS_MS_PT-BR_MARIA_11.0", name="Microsoft Maria"),
    ]

    assert "Maria" in pick_voice(voices, "pt-BR").name


def test_pick_voice_never_falls_back_to_a_known_male_voice():
    voices = [
        SimpleNamespace(id="TTS_MS_PT-BR_DANIEL_11.0", name="Microsoft Daniel"),
    ]

    assert pick_voice(voices, "pt-BR") is None


def test_pick_voice_returns_none_when_missing():
    assert pick_voice(VOICES[:1], "pt-BR") is None


# ---------- falar ----------

class FakeEngine:
    def __init__(self):
        self.properties = {}
        self.said = []
        self.ran = False

    def getProperty(self, name):
        return VOICES

    def setProperty(self, name, value):
        self.properties[name] = value

    def say(self, text):
        self.said.append(text)

    def runAndWait(self):
        self.ran = True


def test_speaker_cleans_text_and_uses_matching_voice():
    engines = []

    def factory():
        engines.append(FakeEngine())
        return engines[-1]

    Pyttsx3Speaker(engine_factory=factory).speak("Oi! 💗", "pt-BR")

    assert engines[0].said == ["Oi!"]
    assert "MARIA" in engines[0].properties["voice"]
    assert engines[0].ran is True


def test_speaker_creates_a_fresh_engine_each_time():
    engines = []

    def factory():
        engines.append(FakeEngine())
        return engines[-1]

    speaker = Pyttsx3Speaker(engine_factory=factory)
    speaker.speak("um")
    speaker.speak("dois")

    assert len(engines) == 2


def test_speaker_says_nothing_for_empty_text():
    engines = []

    def factory():
        engines.append(FakeEngine())
        return engines[-1]

    Pyttsx3Speaker(engine_factory=factory).speak("💗")

    assert engines == []


# ---------- sessão ----------

def test_session_listen_chains_recorder_and_transcriber():
    audio = np.ones(10, dtype="float32")
    seen = []

    class Recorder:
        def record(self):
            return audio

    class Transcriber:
        def transcribe(self, received):
            seen.append(received)
            return "me lembra de estudar"

    session = VoiceSession(Recorder(), Transcriber(), speaker=None)

    assert session.listen() == "me lembra de estudar"
    assert seen == [audio]


def test_session_say_delegates_to_speaker():
    calls = []

    class Speaker:
        def speak(self, text, language):
            calls.append((text, language))

    VoiceSession(None, None, Speaker()).say("oi", "en")

    assert calls == [("oi", "en")]
