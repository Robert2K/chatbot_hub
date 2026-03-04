import os
from dotenv import load_dotenv
from openai import OpenAI
import mimetypes
import base64  #biblioteka kodowania w PYTHONIE, pozwala na kodowanie i dekodowanie danych binarnych do formatu tekstowego (base64), co jest przydatne przy przesyłaniu plików przez API, które oczekuje danych tekstowych.
import hashlib  #biblioteka do tworzenia skrótów (hashy) w PYTHONIE, pozwala na generowanie unikalnych identyfikatorów dla danych, co może być przydatne do cache'owania odpowiedzi lub identyfikowania wiadomości. 
from django.core.cache import cache

load_dotenv()

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
#OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
# Potrzebna aktualna nazwa modelu z https://openrouter.ai/models (filter: Free)
# Przykład: "mistralai/mistral-7b-instruct:free" lub "google/flan-t5-xl:free"
#MODEL = "nvidia/llama-nemotron"
#####MODEL = "openai/gpt-oss-120b:free"
MODEL = "google/gemma-3-27b-it:free"
#MODEL = "nvidia/llama-nemotron-embed-vl-1b-v2:free"
#MODEL = "mistralai/mistral-7b-instruct:free"

client = None
if OPENROUTER_API_KEY:
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY
    )

def build_user_content(messages_obj):
    content = [{"type" : "text", "text" : messages_obj.content}]

    for att in messages_obj.attachments.all():
        file_path = att.file.path
        mime, _ = mimetypes.guess_type(file_path) # _  = podloga (swiadomie ignorujemy jakas wartosc), bo malo nas obchodzi jak plik jest ZAKODOWANY, bo i tak go nie wyślemy do API, ale chcemy mieć info o typie pliku w treści wiadomości.
        #mime zwraca krotke, gdzie pierwszy element to typ MIME, a drugi to podloga (np. 'base64'). Jeśli nie można określić typu, zwraca (None, None).
        mime = mime or "application/octet-stream" # octet/stream jest ciag BITÓW. default, jeśli nie można określić typu.
        with open(file_path, 'rb') as f:  #r=zwykly READ. rb = read binary, czyli otwieramy plik w trybie binarnym, co jest konieczne do poprawnego odczytania zawartości pliku, zwłaszcza jeśli jest to plik nie-tekstowy (np. obraz, PDF, itp.).
            b64 = base64.b64encode(f.read()).decode('utf-8') # kodowanie zawartości pliku do formatu base64, a następnie dekodowanie go do stringa UTF-8, aby można było go bezpiecznie przesłać jako tekst.
            if att.file_type == "img":
                content.append({"type" : "image_url", 
                                "image_url" : f"data:{mime};base64,{b64}"
                                }) 
            # tworzymy specjalny URL danych (data URL), który zawiera zakodowaną zawartość pliku. Format tego URL to: data:[<mediatype>][;base64],<data>. W tym przypadku, <mediatype> to typ MIME pliku, a <data> to zakodowana zawartość pliku w formacie base64.
    
            else: 
                content.append({"type" : "file", 
                                "filename" : att.file.name,
                                "file_data" : f"data:{mime};base64,{b64}"
                                })
        return content



def ask_openrouter(message_obj):
    
    #key = "ai:" + hashlib.md5(message_obj.content.encode()).hexdigest()
    
    key = "ai:" + hashlib.sha256(message_obj.content.encode()).hexdigest() 
    #nowsza metoda HASOWANIA niz metoda MD5. SHA256 jest uważana za bezpieczniejszą i bardziej odporną na kolizje niż MD5, co oznacza, że jest mniej prawdopodobne, że dwie różne wiadomości wygenerują ten sam hash. Dlatego w kontekście cache'owania odpowiedzi AI, SHA256 może być lepszym wyborem do generowania unikalnych kluczy dla wiadomości.
    cashed = cache.get(key)
    if not OPENROUTER_API_KEY:
        return "Demo response (API key nie ustawiony): Dziękuję za pytanie: " + question[:50] + "..."
    if not client:
        return "Demo response: Chatbot nie mógł połączyć się z API"
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role":"user","content":message_obj.content}],
            extra_body={"reasoning": {"enabled": True}}
        )
        answer = response.choices[0].message.content
        cache.set(key, answer, timeout=60*20) # 60sekund * 20 = 20 minut. Oznacza to, że odpowiedź będzie przechowywana w cache'u przez 20 minut. Jeśli ta sama wiadomość zostanie zapytana ponownie w ciągu tych 20 minut, chatbot zwróci odpowiedź z cache'a zamiast ponownie wywoływać API, co może znacznie przyspieszyć odpowiedź i zmniejszyć obciążenie API.
        return answer
    except Exception as e:
        return f"Blad OPENROUTER: {str(e)}"


