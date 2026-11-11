import re

SAMPLE_RATE = 16000
MIN_SECONDS = 0.4
SILENCE_RMS = 0.005

# Vozes femininas preferidas por idioma (nomes das vozes do Windows).
FEMALE_VOICES = {
    "pt": ("maria", "francisca"),
    "en": ("zira", "hazel", "aria", "jenny"),
    "es": ("helena", "sabina", "laura", "paulina"),
}

# Marcadores do idioma, usados só se nenhuma voz feminina estiver instalada.
LANGUAGE_MARKERS = {
    "pt": ("pt-br", "pt_br", "portuguese", "brazil"),
    "en": ("en-us", "en_us", "en-gb", "english"),
    "es": ("es-", "es_", "spanish"),
}

# Vozes masculinas conhecidas: nunca escolhidas como alternativa.
MALE_VOICES = ("daniel", "david", "mark", "pablo", "raul", "george")

LANGUAGE_CODES = {"pt-BR": "pt", "en": "en", "es": "es"}


def clean_for_speech(text):
    """Remove emojis, markdown e símbolos que ficam estranhos quando lidos."""
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"#(\d+)", r"número \1", text)
    text = re.sub(r"[`*_#>~|]", "", text)
    text = re.sub(r"<3", "", text)
    text = re.sub(
        "[\U0001F000-\U0001FAFF☀-➿️‍]", "", text
    )
    text = re.sub(r"\s*\n+\s*", ". ", text)
    return re.sub(r"\s+", " ", text).strip()


def is_silent(audio):
    """True se a gravação é curta demais ou quase só silêncio."""
    import numpy as np

    samples = np.asarray(audio, dtype="float32").reshape(-1)

    if samples.size < SAMPLE_RATE * MIN_SECONDS:
        return True

    return float(np.sqrt(np.mean(samples ** 2))) < SILENCE_RMS


def _label(voice):
    return f"{getattr(voice, 'id', '')} {getattr(voice, 'name', '')}".lower()


def pick_voice(voices, language):
    """
    Escolhe uma voz feminina do idioma. Se não houver, uma voz do idioma
    que não seja masculina. Devolve None se nada servir (usa a voz padrão).
    """
    code = LANGUAGE_CODES.get(language, language)

    for name in FEMALE_VOICES.get(code, ()):
        for voice in voices:
            if name in _label(voice):
                return voice

    for voice in voices:
        label = _label(voice)

        if any(marker in label for marker in LANGUAGE_MARKERS.get(code, ())):
            if not any(male in label for male in MALE_VOICES):
                return voice

    return None


class SoundDeviceRecorder:
    """Grava do microfone: Enter para começar, Enter para parar."""

    def __init__(self, sample_rate=SAMPLE_RATE):
        self.sample_rate = sample_rate

    def record(self):
        import numpy as np
        import sounddevice as sd

        chunks = []

        def callback(indata, frames, time_info, status):
            chunks.append(indata.copy())

        input("  [Enter para começar a falar]")

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            callback=callback,
        ):
            input("  🎙️  Gravando... [Enter para parar]")

        if not chunks:
            return np.zeros(0, dtype="float32")

        return np.concatenate(chunks).reshape(-1)


class WhisperTranscriber:
    """Transcrição local com faster-whisper (carrega o modelo na 1ª vez)."""

    def __init__(self, model_size="small", device="cpu", compute_type="int8"):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None

    def transcribe(self, audio):
        if is_silent(audio):
            return ""

        if self._model is None:
            from faster_whisper import WhisperModel

            print("  (carregando o modelo de voz, só na primeira vez...)")
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )

        segments, _info = self._model.transcribe(
            audio,
            vad_filter=True,
            language=None,
            condition_on_previous_text=False,
        )

        return " ".join(segment.text.strip() for segment in segments).strip()


class Pyttsx3Speaker:
    """Fala com as vozes instaladas no Windows (SAPI), sem internet."""

    def __init__(self, engine_factory=None, rate=185):
        if engine_factory is None:
            import pyttsx3

            engine_factory = pyttsx3.init

        self.engine_factory = engine_factory
        self.rate = rate

    def speak(self, text, language="pt-BR"):
        text = clean_for_speech(text)

        if not text:
            return

        # Engine novo a cada fala: evita travar na segunda chamada no Windows.
        engine = self.engine_factory()
        voice = pick_voice(engine.getProperty("voices"), language)

        if voice is not None:
            engine.setProperty("voice", voice.id)

        engine.setProperty("rate", self.rate)
        engine.say(text)
        engine.runAndWait()


class VoiceSession:
    def __init__(self, recorder, transcriber, speaker):
        self.recorder = recorder
        self.transcriber = transcriber
        self.speaker = speaker

    def listen(self):
        """Grava e devolve o texto falado ('' se não entendeu nada)."""
        return self.transcriber.transcribe(self.recorder.record())

    def say(self, text, language="pt-BR"):
        self.speaker.speak(text, language)


def create_voice_session():
    """
    Monta a sessão de voz real. Levanta ImportError se as dependências
    opcionais (requirements-voice.txt) não estiverem instaladas.
    """
    import faster_whisper  # noqa: F401
    import numpy  # noqa: F401
    import pyttsx3  # noqa: F401
    import sounddevice  # noqa: F401

    return VoiceSession(
        SoundDeviceRecorder(),
        WhisperTranscriber(),
        Pyttsx3Speaker(),
    )
