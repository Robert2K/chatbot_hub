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

from django.shortcuts import render, redirect, get_object_or_404
from .models import ChatSession, ChatMessage, Attachment, AudioMessage
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import login, logout, authenticate
from .openrouter import ask_openrouter
from .utils import mime_dictionary, generate_tts_file
from django.core.files.base import ContentFile


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
    Display session and handle message/file submissions with attachment validation.
    
    Validates: message/file required, file size ≤10MB, file type allowed.
    Attachments: Limited to 1 per message. Supports all FILE_TYPES from models.py (max 10MB).
    Creates ChatMessage for user and AI response via OpenRouter API.
    
    Args:
        request (HttpRequest): GET displays session, POST processes messages.
        session_id (int): Session primary key.
    
    POST Data:
        message (str, optional): User message text.
        file (UploadedFile, optional): File attachment (all supported types).
    
    Returns:
        HttpResponse: Session template or error/redirect response.
    """
    # MIME type to file_type mapping based on models.Attachment.FILE_TYPES
    # Maps browser-provided MIME types to database file_type classification codes
    MIME_TO_FILETYPE = {
        # Documents
        'text/plain': 'txt',
        'application/rtf': 'rtf',
        'application/msword': 'doc',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
        'application/vnd.ms-excel': 'xls',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'pptx',
        'application/pdf': 'pdf',
        'text/html': 'html',
        'text/css': 'css',
        'text/csv': 'csv',
        # Images
        'image/jpeg': 'jpg',
        'image/png': 'png',
        'image/gif': 'gif',
        'image/x-icon': 'ico',
        'image/vnd.microsoft.icon': 'ico',
        # Audio
        'audio/mpeg': 'mp3',
        'audio/x-mp3': 'mp3',
        'audio/mp4': 'mp4',
        # Video
        'video/x-msvideo': 'avi',
        'video/mp4': 'mp4',
        # Archives
        'application/zip': 'zip',
        'application/x-zip-compressed': 'xzip',
        'application/x-rar-compressed': 'rar',
        'application/x-7z-compressed': '7zip',
    }
    
    # All MIME types allowed for validation (derived from MIME_TO_FILETYPE keys)
    ALLOWED = list(MIME_TO_FILETYPE.keys())
   
    MAX_SIZE = 10 * 1024 * 1024  # 10 MB  (1024Bytex1024Byte=1MegaByte)

    # Generate supported file extensions list for dynamic error messages
    # Maps file_type codes to display extensions for user-friendly error messages
    SUPPORTED_EXTENSIONS = {
        'txt': '.txt',
        'rtf': '.rtf',
        'doc': '.doc',
        'docx': '.docx',
        'xls': '.xls',
        'xlsx': '.xlsx',
        'pptx': '.pptx',
        'pdf': '.pdf',
        'jpg': '.jpg, .jpeg',
        'png': '.png',
        'ico': '.ico',
        'gif': '.gif',
        'mp3': '.mp3',
        'mp4': '.mp4',
        'avi': '.avi',
        'zip': '.zip',
        'xzip': '.zip (compressed)',
        'rar': '.rar',
        '7zip': '.7z',
        'html': '.html',
        'css': '.css',
        'csv': '.csv',
    }

    session = get_object_or_404(ChatSession, id=session_id, user=request.user)
    
    if request.method == 'POST':
        text = request.POST.get('message', '').strip()
        file = request.FILES.get('file')
        
        # Validation: message or file required
        if not text and not file:
            return render(request, 'chat/session_detail.html',
                          {"session": session,
                           "error": "Message or file is required."})
        
        if text:
            # Check if previous user message in session has attachment
            last_user_msg = ChatMessage.objects.filter(
                session=session, role='user'
            ).order_by('-created_at').first()
            
            # Enforce: max 1 attachment in consecutive user messages
            if file and last_user_msg and last_user_msg.attachments.exists():
                return render(request, 'chat/session_detail.html',
                              {"session": session,
                               "error": "Previous message already has attachment. Maximum 1 file per message allowed."})
            
            # Create user message
            msg = ChatMessage.objects.create(session=session, role='user', content=text)
            
            # Handle file attachment if provided
            if file:
                # Validate file size
                if file.size > MAX_SIZE:
                    msg.delete()
                    return render(request, 'chat/session_detail.html',
                                  {"session": session,
                                   "error": "File is too large. Maximum 10MB allowed."})
                
                # Validate file type against MIME_TO_FILETYPE mapping
                # Dynamically displays all supported file types in error message
                if file.content_type not in MIME_TO_FILETYPE:
                    msg.delete()
                    # Comprehensive error message listing all supported file types
                    supported_types = ", ".join(sorted(set(SUPPORTED_EXTENSIONS.values())))
                    return render(request, 'chat/session_detail.html',
                                  {"session": session,
                                   "error": f"File type not allowed. Supported: {supported_types} (max 10MB)"})
                
                # Determine file_type from MIME type using mapping
                # Ensures database file_type matches file classification in FILE_TYPES
                file_type = MIME_TO_FILETYPE[file.content_type]
                Attachment.objects.create(message=msg, file=file, file_type=file_type, size=file.size)
            
            # Get AI response and create assistant message
            reply = ask_openrouter(msg)  #ChatMessage przy Text-to-Speech-Agencie zamieniamy na 
            #AudioMessage, ale to będzie wymagało przebudowy logiki w openrouter.py, 
            #żeby zwracał odpowiedź audio zamiast tekstowej.
            assistant_msg = ChatMessage.objects.create(session=session, role='assistant', content=reply)
            audio_bytes = generate_tts_file(reply)
            audio = AudioMessage.objects.create(message=assistant_msg)
            audio.file.save('reply.mp3', ContentFile(audio_bytes))
                        
        return redirect('session_detail', session_id=session.id)
    return render(request, 'chat/session_detail.html', {'session': session})
    
 


def login_view(request):
    """
    Handle user authentication using AuthenticationForm.
    
    Redirect authenticated users to home. Display login form for anonymous users.
    
    Args:
        request (HttpRequest): GET shows form, POST validates credentials.
    
    POST Data:
        username (str): User's username.
        password (str): User's password.
    
    Returns:
        HttpResponse: Form template or redirect to 'home' on success.
    """
    # Redirect if already authenticated
    if request.user.is_authenticated:
        return redirect('home')
    
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
    Redirect authenticated users to home.
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
    # Redirect if already authenticated
    if request.user.is_authenticated:
        return redirect('home')
    
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

   