"""Django ORM models for chatbot_hub chat application.

Models:
    - ChatSession: User conversation container
    - ChatMessage: Individual messages (user/assistant)
    - Attachment: File attachments to messages

Reference:
    https://docs.djangoproject.com/en/5.2/topics/db/models/
"""

from django.db import models
from django.contrib.auth.models import User


class ChatSession(models.Model):
    """User conversation session container.
    
    Attributes:
        name (str): Session display name (max 255 chars).
        user (ForeignKey): Link to Django User model (CASCADE delete).
        created_at (DateTime): Automatic timestamp on creation.
    """
    name = models.CharField(max_length=255)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_sessions')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        """Return session name for admin/shell representation."""
        return self.name


class ChatMessage(models.Model):
    """Individual message in a chat session.
    
    Attributes:
        session (ForeignKey): Parent ChatSession (CASCADE delete).
        role (CharField): 'user' or 'assistant' from ROLE_CHOICES.
        content (TextField): Message text.
        created_at (DateTime): Automatic timestamp on creation.
    """
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
    ]
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        """Return role and first 30 chars of content for admin representation."""
        return f"{self.role}: {self.content[:30]}"


class Attachment(models.Model):
    """File attachment associated with a message.
    
    Attributes:
        message (ForeignKey): Parent ChatMessage (CASCADE delete).
        file (FileField): Uploaded file (stored in 'attachments/' directory).
        file_type (CharField): File category from FILE_TYPES choices.
        size (IntegerField): File size in bytes.
        created_at (DateTime): Automatic timestamp on creation.
    """
    FILE_TYPES = [
        ('txt', 'Text File'),
        ('rtf', 'Rich Text Format'),
        ('doc', 'Word Document'),
        ('docx', 'Word Document'),
        ('xls', 'Excel Spreadsheet'),
        ('xlsx', 'Excel Spreadsheet'),
        ('pptx', 'PowerPoint Presentation'),
        ('pdf', 'PDF Document'),
        ('img', 'Image File'),
        ('jpg', 'JPEG Image'),
        ('png', 'PNG Image'),
        ('ico', 'Icon Image'),
        ('gif', 'GIF Image'),
        ('mp3', 'MP3 Audio'),
        ('avi', 'AVI Video'),
        ('mp4', 'MP4 Video'),
        ('zip', 'ZIP Archive'),
        ('xzip', 'ZIP Archive'),
        ('rar', 'RAR Archive'),
        ('7zip', '7-Zip Archive'),
        ('html', 'HTML File'),
        ('css', 'CSS File'),
        ('csv', 'CSV File'),
    ]

    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='attachments/')
    file_type = models.CharField(max_length=40, choices=FILE_TYPES)
    size = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        """Return filename and file type for admin representation."""
        return f"{self.file.name} ({self.file_type})"


class AudioMessage(models.Model):
    """Audio response associated with an assistant message.
    
    Attributes:
        message (ForeignKey): Parent ChatMessage (CASCADE delete).
        file (FileField): Audio file (stored in 'audio/' directory).
        created_at (DateTime): Automatic timestamp on creation.
    """
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name='audio')
    file = models.FileField(upload_to='audio/')
    created_at = models.DateTimeField(auto_now_add=True)
#After that, you need to build logic in views (views.py) for it to work.
