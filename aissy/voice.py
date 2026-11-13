import re

SAMPLE_RATE = 16000
ALLOWED_LANGUAGES = {"pt", "en", "es"}
MIN_LANGUAGE_PROBABILITY = 0.4
MAX_NO_SPEECH_PROB = 0.6
MIN_AVG_LOGPROB = -1.0

# Ajuda o Whisper a acertar nomes próprios que ele não conhece.
VOCABULARY_PROMPT = (
    "Conversa informal com a AISSY, assistente pessoal da Ge (também chamada "
    "de Noxie). Palavras: AISSY, Ge, Noxie, UFU Racing, TikTok, Python, "
    "Ollama, iFood."
)
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
    text = re.sub(r"```.*?```", " Deixei o código na tela. ", text, flags=re.S)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"#(\d+)", r"número \1", text)
    text = re.sub(r"[`*_#>~|]", "", text)
    text = re.sub(r"<3", "", text)
    text = re.sub(
        "[\U0001F000-\U0001FAFF☀-➿️‍]", "", text
    )
    text = re.sub(r"\s*\n+\s*", ". ", text)
    return re.sub(r"\s+", " ", text).strip()


EXIT_PHRASES = {
    "sair", "tchau", "tchau aissy", "até mais", "até logo", "encerrar",
    "exit", "bye", "goodbye", "adiós",
}

NOISE_MARKERS = (
    "legendas pela comunidade", "amara.org", "thanks for watching",
    "inscreva-se", "subtitles by",
)


def _normalize(text):
    return re.sub(r"[^\w\sà-ÿ]", "", text.lower()).strip()


def is_exit_phrase(text):
    """True se a pessoa só disse 'tchau', 'sair' etc."""
    return _normalize(text) in EXIT_PHRASES


NON_LATIN = re.compile(
    "[\u0400-\u04FF\u0590-\u06FF\u0900-\u0DFF\u0E00-\u0E7F"
    "\u3040-\u30FF\u4E00-\u9FFF\uAC00-\uD7AF]"
)


def is_noise_transcript(text):
    """Frases que o Whisper inventa quando só há ruído."""
    lowered = text.lower()

    if NON_LATIN.search(text):
        return True

    return any(marker in lowered for marker in NOISE_MARKERS)


class AutoStopDetector:
    """
    Decide quando parar de gravar sem apertar Enter: espera você começar a
    falar e para depois de um tempo de silêncio. Desiste se ninguém falar.
    """

    def __init__(
        self,
        threshold,
        silence_seconds=1.2,
        wait_seconds=8.0,
        max_seconds=30.0,
    ):
        self.threshold = threshold
        self.silence_seconds = silence_seconds
        self.wait_seconds = wait_seconds
        self.max_seconds = max_seconds
        self.elapsed = 0.0
        self.silence_run = 0.0
        self.speaking = False

    def feed(self, rms, block_seconds):
        """Devolve 'continue', 'stop' (tem fala) ou 'timeout' (ninguém falou)."""
        self.elapsed += block_seconds

        if rms >= self.threshold:
            self.speaking = True
            self.silence_run = 0.0
        else:
            self.silence_run += block_seconds

        if self.speaking and self.silence_run >= self.silence_seconds:
            return "stop"

        if self.elapsed >= self.max_seconds:
            return "stop" if self.speaking else "timeout"

        if not self.speaking and self.elapsed >= self.wait_seconds:
            return "timeout"

        return "continue"


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


    def record_auto(self):
        """Ouve sozinho: começa quando você fala e para no silêncio."""
        import queue

        import numpy as np
        import sounddevice as sd

        block_seconds = 0.1
        blocks = queue.Queue()
        chunks = []

        def callback(indata, frames, time_info, status):
            blocks.put(indata.copy())

        detector = None
        ambient = []

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            blocksize=int(self.sample_rate * block_seconds),
            callback=callback,
        ):
            while True:
                block = blocks.get()
                rms = float(np.sqrt(np.mean(block ** 2)))
                chunks.append(block)

                # Primeiros 0,4 s: mede o ruído do ambiente.
                if detector is None:
                    ambient.append(rms)

                    if len(ambient) >= 4:
                        noise = sum(ambient) / len(ambient)
                        detector = AutoStopDetector(max(0.012, noise * 3))

                    continue

                state = detector.feed(rms, block_seconds)

                if state == "timeout":
                    return np.zeros(0, dtype="float32")

                if state == "stop":
                    return np.concatenate(chunks).reshape(-1)


class WhisperTranscriber:
    """Transcrição local com faster-whisper (carrega o modelo na 1ª vez)."""

    def __init__(
        self,
        model_size="small",
        device="cpu",
        compute_type="int8",
        model=None,
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = model

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

        segments, info = self._model.transcribe(
            audio,
            vad_filter=True,
            language=None,
            condition_on_previous_text=False,
            initial_prompt=VOCABULARY_PROMPT,
        )

        # Ruído vira texto em idiomas aleatórios: só aceita pt, en e es.
        if (
            info.language not in ALLOWED_LANGUAGES
            or info.language_probability < MIN_LANGUAGE_PROBABILITY
        ):
            return ""

        kept = [
            segment.text.strip()
            for segment in segments
            if getattr(segment, "no_speech_prob", 0.0) < MAX_NO_SPEECH_PROB
            and getattr(segment, "avg_logprob", 0.0) > MIN_AVG_LOGPROB
        ]

        return " ".join(kept).strip()


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


EDGE_PREFERRED_FEMALE = {
    "pt": ("Francisca", "Thalita"),
    "en": ("Aria", "Jenny"),
    "es": ("Elvira", "Dalia"),
}

EDGE_LOCALE_PREFIX = {"pt": "pt-BR", "en": "en-US", "es": "es-"}


def pick_edge_voice(voices, language):
    """
    Escolhe uma voz neural feminina do idioma, entre as que o serviço lista
    (dicionários com ShortName, Gender e Locale). None se não houver.
    """
    code = LANGUAGE_CODES.get(language, language)
    prefix = EDGE_LOCALE_PREFIX.get(code)

    if prefix is None:
        return None

    female = [
        voice for voice in voices
        if voice.get("Gender") == "Female"
        and str(voice.get("Locale", "")).startswith(prefix)
    ]

    for name in EDGE_PREFERRED_FEMALE.get(code, ()):
        for voice in female:
            if name in voice.get("ShortName", ""):
                return voice["ShortName"]

    return female[0]["ShortName"] if female else None


def _edge_list_voices():
    import asyncio

    import edge_tts

    return asyncio.run(edge_tts.list_voices())


def _edge_synthesize(text, voice):
    """Texto -> bytes de áudio mp3, pelo serviço online do Edge."""
    import asyncio

    import edge_tts

    async def run():
        audio = b""

        async for chunk in edge_tts.Communicate(text, voice).stream():
            if chunk["type"] == "audio":
                audio += chunk["data"]

        return audio

    return asyncio.run(run())


def _play_mp3(audio):
    import miniaudio
    import numpy as np
    import sounddevice as sd

    decoded = miniaudio.decode(
        audio,
        output_format=miniaudio.SampleFormat.SIGNED16,
        nchannels=1,
    )
    samples = np.frombuffer(decoded.samples, dtype="int16")

    try:
        sd.play(samples, decoded.sample_rate)
        sd.wait()
    except KeyboardInterrupt:
        sd.stop()
        raise


class EdgeTTSSpeaker:
    """
    Voz neural, bem mais natural. ATENÇÃO: o texto das respostas é enviado
    ao serviço online da Microsoft para gerar o áudio (é opcional).
    """

    def __init__(self, synthesize=None, play=None, list_voices=None):
        self.synthesize = synthesize or _edge_synthesize
        self.play = play or _play_mp3
        self.list_voices = list_voices or _edge_list_voices
        self._voices = None

    def _voice_for(self, language):
        if self._voices is None:
            self._voices = self.list_voices()

        return pick_edge_voice(self._voices, language)

    def speak(self, text, language="pt-BR"):
        text = clean_for_speech(text)

        if not text:
            return

        voice = self._voice_for(language)

        if voice is None:
            raise RuntimeError(f"No neural voice found for {language}.")

        self.play(self.synthesize(text, voice))


class FallbackSpeaker:
    """Tenta a voz principal; se falhar (sem internet, por exemplo), usa a local."""

    def __init__(self, primary, fallback):
        self.primary = primary
        self.fallback = fallback
        self.warned = False

    def speak(self, text, language="pt-BR"):
        try:
            self.primary.speak(text, language)
        except Exception as error:
            if not self.warned:
                print(f"  (voz online indisponível, usando a local: {error})")
                self.warned = True

            self.fallback.speak(text, language)


class VoiceSession:
    def __init__(self, recorder, transcriber, speaker):
        self.recorder = recorder
        self.transcriber = transcriber
        self.speaker = speaker

    def listen(self, auto=False):
        """Grava e devolve o texto falado ('' se não entendeu nada)."""
        audio = self.recorder.record_auto() if auto else self.recorder.record()
        text = self.transcriber.transcribe(audio)

        return "" if is_noise_transcript(text) else text

    def say(self, text, language="pt-BR"):
        self.speaker.speak(text, language)


def create_voice_session(online=False):
    """
    Monta a sessão de voz real. Levanta ImportError se as dependências
    opcionais (requirements-voice.txt) não estiverem instaladas.
    online=True usa vozes neurais (requirements-voice-online.txt), com a
    voz local como reserva.
    """
    import faster_whisper  # noqa: F401
    import numpy  # noqa: F401
    import pyttsx3  # noqa: F401
    import sounddevice  # noqa: F401

    speaker = Pyttsx3Speaker()

    if online:
        import edge_tts  # noqa: F401
        import miniaudio  # noqa: F401

        speaker = FallbackSpeaker(EdgeTTSSpeaker(), speaker)

    return VoiceSession(
        SoundDeviceRecorder(),
        WhisperTranscriber(),
        speaker,
    )
