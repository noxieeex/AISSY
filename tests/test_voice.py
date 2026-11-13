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


# ---------- ouvir sozinho ----------

from aissy.voice import AutoStopDetector, is_exit_phrase, is_noise_transcript


def run(detector, levels, block=0.1):
    for level in levels:
        state = detector.feed(level, block)

        if state != "continue":
            return state

    return "continue"


def test_stops_after_silence_following_speech():
    detector = AutoStopDetector(threshold=0.02, silence_seconds=1.0)

    assert run(detector, [0.0] * 5 + [0.1] * 10 + [0.0] * 20) == "stop"


def test_does_not_stop_during_a_short_pause():
    detector = AutoStopDetector(threshold=0.02, silence_seconds=1.0)

    assert run(detector, [0.1] * 10 + [0.0] * 5 + [0.1] * 10) == "continue"


def test_times_out_when_nobody_speaks():
    detector = AutoStopDetector(threshold=0.02, wait_seconds=2.0)

    assert run(detector, [0.0] * 50) == "timeout"


def test_stops_at_max_length_even_if_still_talking():
    detector = AutoStopDetector(threshold=0.02, max_seconds=3.0)

    assert run(detector, [0.1] * 100) == "stop"


@pytest.mark.parametrize(
    "text", ["Tchau!", "sair", "Até mais.", "exit", "Tchau, AISSY"[:5] + "!"]
)
def test_exit_phrases(text):
    assert is_exit_phrase(text)


@pytest.mark.parametrize("text", ["tchau, mas antes me lembra de X", "oi", ""])
def test_normal_phrases_are_not_exit(text):
    assert not is_exit_phrase(text)


def test_whisper_noise_artifacts_are_detected():
    assert is_noise_transcript("Legendas pela comunidade Amara.org")
    assert not is_noise_transcript("me lembra de estudar")


def test_session_drops_noise_transcripts():
    class Recorder:
        def record(self):
            return None

        def record_auto(self):
            return "auto"

    class Transcriber:
        def transcribe(self, audio):
            return "Legendas pela comunidade Amara.org"

    assert VoiceSession(Recorder(), Transcriber(), None).listen(auto=True) == ""


def test_session_uses_auto_recorder_when_asked():
    calls = []

    class Recorder:
        def record(self):
            calls.append("manual")

        def record_auto(self):
            calls.append("auto")

    class Transcriber:
        def transcribe(self, audio):
            return "oi"

    session = VoiceSession(Recorder(), Transcriber(), None)
    session.listen(auto=True)
    session.listen()

    assert calls == ["auto", "manual"]


def test_code_blocks_are_not_read_aloud():
    cleaned = clean_for_speech("Faz assim:\n```python\nprint(1)\n```\nPronto!")

    assert "print" not in cleaned
    assert "código na tela" in cleaned


# ---------- filtros contra texto inventado a partir de ruído ----------

def speech_audio():
    t = np.linspace(0, 2, SAMPLE_RATE * 2, dtype="float32")
    return 0.3 * np.sin(2 * np.pi * 220 * t)


def fake_model(language, probability, segments):
    class Model:
        def transcribe(self, audio, **kwargs):
            info = SimpleNamespace(
                language=language,
                language_probability=probability,
            )
            return iter(segments), info

    return Model()


def seg(text, no_speech=0.0, logprob=-0.2):
    return SimpleNamespace(
        text=text, no_speech_prob=no_speech, avg_logprob=logprob
    )


def test_transcriber_returns_good_segments():
    model = fake_model("pt", 0.95, [seg(" oi"), seg(" tudo bem?")])

    assert WhisperTranscriber(model=model).transcribe(speech_audio()) == "oi tudo bem?"


def test_transcriber_rejects_unexpected_language():
    model = fake_model("ko", 0.9, [seg("대시지 대시지")])

    assert WhisperTranscriber(model=model).transcribe(speech_audio()) == ""


def test_transcriber_rejects_low_language_confidence():
    model = fake_model("pt", 0.1, [seg("hmm")])

    assert WhisperTranscriber(model=model).transcribe(speech_audio()) == ""


def test_transcriber_drops_dubious_segments():
    model = fake_model(
        "pt", 0.9,
        [seg("oi"), seg("lixo", no_speech=0.9), seg("mais lixo", logprob=-2.0)],
    )

    assert WhisperTranscriber(model=model).transcribe(speech_audio()) == "oi"


def test_non_latin_text_is_noise():
    assert is_noise_transcript("대시지 대시지")
    assert is_noise_transcript("ありがとう")
    assert not is_noise_transcript("olá, tudo bem? ¿cómo estás?")


def test_transcriber_sends_vocabulary_prompt():
    received = {}

    class Model:
        def transcribe(self, audio, **kwargs):
            received.update(kwargs)
            return iter([]), SimpleNamespace(language="pt", language_probability=0.9)

    WhisperTranscriber(model=Model()).transcribe(speech_audio())

    assert "AISSY" in received["initial_prompt"]
    assert "UFU Racing" in received["initial_prompt"]


# ---------- voz neural (opcional) ----------

from aissy.voice import EdgeTTSSpeaker, FallbackSpeaker, pick_edge_voice

EDGE_VOICES = [
    {"ShortName": "pt-BR-AntonioNeural", "Gender": "Male", "Locale": "pt-BR"},
    {"ShortName": "pt-BR-ThalitaNeural", "Gender": "Female", "Locale": "pt-BR"},
    {"ShortName": "pt-BR-FranciscaNeural", "Gender": "Female", "Locale": "pt-BR"},
    {"ShortName": "pt-PT-RaquelNeural", "Gender": "Female", "Locale": "pt-PT"},
    {"ShortName": "en-US-GuyNeural", "Gender": "Male", "Locale": "en-US"},
    {"ShortName": "en-US-AriaNeural", "Gender": "Female", "Locale": "en-US"},
    {"ShortName": "es-ES-ElviraNeural", "Gender": "Female", "Locale": "es-ES"},
]


@pytest.mark.parametrize(
    "language, expected",
    [
        ("pt-BR", "pt-BR-FranciscaNeural"),
        ("en", "en-US-AriaNeural"),
        ("es", "es-ES-ElviraNeural"),
    ],
)
def test_pick_edge_voice_prefers_known_female_voices(language, expected):
    assert pick_edge_voice(EDGE_VOICES, language) == expected


def test_pick_edge_voice_never_returns_male_or_other_locale():
    male_only = [EDGE_VOICES[0], EDGE_VOICES[3]]

    assert pick_edge_voice(male_only, "pt-BR") is None


def test_pick_edge_voice_falls_back_to_any_female_in_locale():
    voices = [{"ShortName": "pt-BR-OutraNeural", "Gender": "Female", "Locale": "pt-BR"}]

    assert pick_edge_voice(voices, "pt-BR") == "pt-BR-OutraNeural"


def test_pick_edge_voice_unknown_language():
    assert pick_edge_voice(EDGE_VOICES, "ja") is None


def test_edge_speaker_synthesizes_and_plays_cleaned_text():
    calls = {}

    speaker = EdgeTTSSpeaker(
        synthesize=lambda text, voice: calls.update(text=text, voice=voice) or b"mp3",
        play=lambda audio: calls.update(audio=audio),
        list_voices=lambda: EDGE_VOICES,
    )

    speaker.speak("Oi, Ge! 💗", "pt-BR")

    assert calls == {"text": "Oi, Ge!", "voice": "pt-BR-FranciscaNeural", "audio": b"mp3"}


def test_edge_speaker_lists_voices_only_once():
    count = {"n": 0}

    def list_voices():
        count["n"] += 1
        return EDGE_VOICES

    speaker = EdgeTTSSpeaker(
        synthesize=lambda t, v: b"x", play=lambda a: None, list_voices=list_voices
    )
    speaker.speak("um", "pt-BR")
    speaker.speak("dois", "pt-BR")

    assert count["n"] == 1


def test_edge_speaker_ignores_empty_text():
    speaker = EdgeTTSSpeaker(
        synthesize=lambda t, v: pytest.fail("não deveria sintetizar"),
        play=lambda a: None,
        list_voices=lambda: EDGE_VOICES,
    )

    speaker.speak("💗")


def test_fallback_speaker_uses_local_voice_when_online_fails(capsys):
    spoken = []

    class Broken:
        def speak(self, text, language):
            raise ConnectionError("sem internet")

    class Local:
        def speak(self, text, language):
            spoken.append(text)

    speaker = FallbackSpeaker(Broken(), Local())
    speaker.speak("oi", "pt-BR")
    speaker.speak("tchau", "pt-BR")

    assert spoken == ["oi", "tchau"]
    assert capsys.readouterr().out.count("voz online indisponível") == 1


def test_fallback_speaker_does_not_swallow_ctrl_c():
    class Interrupted:
        def speak(self, text, language):
            raise KeyboardInterrupt

    speaker = FallbackSpeaker(Interrupted(), object())

    with pytest.raises(KeyboardInterrupt):
        speaker.speak("oi", "pt-BR")
