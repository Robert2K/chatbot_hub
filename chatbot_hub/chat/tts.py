from gtts import gTTS
from django.core.files.base import ContentFile
import io
from .models import AudioMessage
 
def generate_tts_file(text):
    mp3 = gTTS(text=text, tld="com", lang='en')
    buffer = io.BytesIO()
    mp3.write_to_fp(buffer)
    buffer.seek(0)
    return buffer.getvalue()
 
 
def create_audio_message(text, assistant_msg):
    audio_bytes = generate_tts_file(text)
    audio = AudioMessage.objects.create(message=assistant_msg)
    audio.file.save('reply.mp3', ContentFile(audio_bytes))


