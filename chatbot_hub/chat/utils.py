def mime_dictionary(): 
# openai rzada pliki w formacie base64 (kodowane), ale z odpowiednim MIME TYPE, 
# dlatego potrzebujemy slownika rozszerzen i odpowiadajacych im MIME TYPE.
    return {
        "txt": "text/plain",
        "pdf": "application/pdf",
        "doc": "application/msword",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "xls": "application/vnd.ms-excel",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "ppt": "application/vnd.ms-powerpoint",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "jpg": "image/jpeg",
        #"jpeg": "image/jpeg",
        #"png": "image/png",
        "gif": "image/gif",
        "img": "image/png", #domyslnie traktujemy "img" jako PNG, ale można to dostosować w zależności od potrzeb
        "img": "image/jpeg", #domyslnie traktujemy "img" jako JPEG, ale można to dostosować w zależności od potrzeb




        # Dodaj więcej rozszerzeń i ich odpowiadających typów MIME w razie potrzeby
    }


