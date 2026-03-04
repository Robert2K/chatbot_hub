"""Django views for chatbot_hub chat application.

This module contains view functions that handle HTTP requests and responses for the chatbot
application. It implements user authentication, session management, and message processing
functionality using Django's built-in authentication system and ORM.

Views:
    - home: Displays list of user's chat sessions
    - session_create: Creates a new chat session
    - session_detail: Displays specific session and handles message/file submissions
    - login_view: Authenticates user with credentials
    - register_view: Creates new user account
    - logout_view: Terminates user session

Reference:
    https://docs.djangoproject.com/en/5.2/topics/http/views/
    https://docs.djangoproject.com/en/5.2/topics/auth/
"""

from django.shortcuts import redirect, render, get_object_or_404
from .models import Attachment, ChatSession, ChatMessage
from .openrouter import ask_openrouter
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import authenticate, login, logout
from.utils import mime_dictionary # z pliku utils.py imprtujemy funkcje mime_dictionary, która zwraca słownik rozszerzeń plików i odpowiadających im typów MIME, co jest potrzebne do prawidłowego obsługiwania załączników w wiadomościach.



@login_required
def home(request):
    """
    Display user's chat sessions ordered by creation date (most recent first).
    
    Args:
        request (HttpRequest): Authenticated user request object.
    
    Returns:
        HttpResponse: Rendered 'chat/home.html' with 'sessions' context.
    """
    sessions = ChatSession.objects.filter(user=request.user).order_by('-created_at')

    return render(request, 'chat/home.html',
                  {'sessions': sessions})

@login_required
def session_create(request):
    """
    Create new chat session for authenticated user.
    
    Args:
        request (HttpRequest): GET displays form, POST creates session.
    
    POST Data:
        name (str, optional): Session name. Defaults to 'New chat'.
    
    Returns:
        HttpResponse: Form template or redirect to created session.
    """
    if request.method == 'POST':
        name = request.POST.get('name') or 'New chat'
        session = ChatSession.objects.create(user=request.user, name=name)
        return redirect('session_detail', session_id=session.id)
    return render(request, 'chat/session_form.html')
 
@login_required
def session_detail(request, session_id):
    """
    Display session and handle message/file submissions with validation.
    
    Validates: message/file required, file size ≤5MB, file type allowed.
    Creates ChatMessage for user and AI response via OpenRouter API.
    
    Args:
        request (HttpRequest): GET displays session, POST processes messages.
        session_id (int): Session primary key.
    
    POST Data:
        message (str, optional): User message text.
        file (UploadedFile, optional): File attachment.
    
    Returns:
        HttpResponse: Session template or error/redirect response.
    """
    ALLOWED = [
        'text/plain', #txt
        'application/rtf',  #rtf rich textformat
        'application/msword', #MS Word   
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document', #openOffice Word
        'application/vnd.ms-excel', #MS Excel
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', #openOffice Excel
        'application/vnd.openxmlformats-officedocument.presentationml.presentation', #openOffice PowerPoint
        'application/pdf', #PDF
        'image/vnd.microsoft.icon', #Icon
        'image/jpeg', #JPEG
        'image/png', #PNG
        'image/gif', #GIF
        'audio/x-mp3', #MP3
        'audio/mpeg', #MPEG
        'audio/mp4', #MP4
        'video/x-msvideo', #AVI
        'application/zip', #zip
        'application/x-zip-compressed', #compressed zip
        'application/x-rar-compressed', #rar
        'application/x-7z-compressed', #7z
        'text/html', #html    
        'text/css', #css
        'text/csv' #csv
    ]
   
    MAX_SIZE = 5 * 1024 * 1024  # 5 MB  (1024Bytex1024Byte=1MegaByte)


    session = get_object_or_404(ChatSession, id=session_id, user=request.user)
    if request.method == 'POST':
        text = request.POST.get('message', '').strip()
        if not text and 'file' in request.FILES:
            return render(request, 'chat/session_detail.html',
                          {"session" : session,
                           "error" : "File or message should not be empty"})
        if text:
            file = request.FILES.get('file')
            msg = ChatMessage.objects.create(session=session, role='user', content=text)
            
            if file:
                if file.size > MAX_SIZE:
                    return render(request, 'chat/session_detail.html',
                                  {"session" : session,
                                   "error" : "File is too large. Max size is 5MB."}
                                   )
                if file.content_type not in ALLOWED:
                    return render(request, 'chat/session_detail.html',
                                  {"session" : session,
                                   "error" : "File type not allowed."}
                                   )
                
                # Determine file type (img or other)
                file_type = "img" if file.content_type.startswith("image/") else "file"
                Attachment.objects.create(message=msg, file=file, file_type=file_type, size=file.size)
            
            reply = ask_openrouter(msg)
            ChatMessage.objects.create(session=session, role='assistant', content=reply)
        return redirect('session_detail', session_id=session.id)
    return render(request, 'chat/session_detail.html', {'session': session})
    
 


def login_view(request):
    """
    Handle user authentication using AuthenticationForm.
    
    Args:
        request (HttpRequest): GET shows form, POST validates credentials.
    
    POST Data:
        username (str): User's username.
        password (str): User's password.
    
    Returns:
        HttpResponse: Form template or redirect to 'home' on success.
    """
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('home')
    else:  # If the request method is not POST, create a new empty form (cDOCKSTRING)
        form = AuthenticationForm()
    return render(request, 'chat/login.html', {'form': form})


def register_view(request):
    """
    Handle user registration with UserCreationForm and auto-login.
    
    Validates username uniqueness and password strength (per AUTH_PASSWORD_VALIDATORS).
    Auto-authenticates user after successful account creation.
    
    Args:
        request (HttpRequest): GET shows form, POST creates and logs in user.
    
    POST Data:
        username (str): Desired username (validated for uniqueness).
        password1 (str): Password (validated against configured validators).
        password2 (str): Password confirmation (must match password1).
    
    Returns:
        HttpResponse: Form template or redirect to 'home' on success.
    """
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'chat/register.html', {'form': form})


@login_required
def logout_view(request):
    """
    Terminate authenticated user session and redirect to home.
    
    Clears session data, deletes session cookie, and sets request.user to AnonymousUser.
    
    Args:
        request (HttpRequest): Authenticated user request object.
    
    Returns:
        HttpResponse: Redirect to 'home' view (HTTP 302).
    """
    logout(request)
    return redirect('home')

   