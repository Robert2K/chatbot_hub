import tempfile
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import AudioMessage, ChatMessage, ChatSession


@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class AuthAndTtsTests(TestCase):
	def setUp(self):
		self.username = 'tester'
		self.password = 'StrongPass123!'

	def test_register_view_creates_user_and_logs_in(self):
		response = self.client.post(
			reverse('register'),
			{
				'username': self.username,
				'password1': self.password,
				'password2': self.password,
			},
		)

		self.assertEqual(response.status_code, 302)
		self.assertRedirects(response, reverse('home'))
		self.assertTrue(User.objects.filter(username=self.username).exists())
		self.assertIn('_auth_user_id', self.client.session)

	def test_login_view_logs_user_in(self):
		User.objects.create_user(username=self.username, password=self.password)

		response = self.client.post(
			reverse('login'),
			{'username': self.username, 'password': self.password},
		)

		self.assertEqual(response.status_code, 302)
		self.assertRedirects(response, reverse('home'))
		self.assertIn('_auth_user_id', self.client.session)

	def test_logout_view_logs_user_out(self):
		user = User.objects.create_user(username=self.username, password=self.password)
		self.client.force_login(user)

		response = self.client.get(reverse('logout'))

		self.assertEqual(response.status_code, 302)
		self.assertEqual(response.url, reverse('home'))
		self.assertNotIn('_auth_user_id', self.client.session)

	@patch('chat.views.ask_openrouter', return_value='AI reply')
	@patch('chat.views.generate_tts_file', return_value=b'mp3-bytes')
	def test_session_detail_with_tts_creates_audio_message(self, mock_tts, _mock_ai):
		user = User.objects.create_user(username=self.username, password=self.password)
		session = ChatSession.objects.create(user=user, name='Session TTS')
		self.client.force_login(user)

		response = self.client.post(
			reverse('session_detail', kwargs={'session_id': session.id}),
			{
				'message': 'Hello with voice',
				'tts': 'on',
			},
		)

		self.assertEqual(response.status_code, 302)
		self.assertEqual(ChatMessage.objects.filter(session=session, role='assistant').count(), 1)
		self.assertEqual(AudioMessage.objects.filter(message__session=session).count(), 1)
		mock_tts.assert_called_once()

	@patch('chat.views.ask_openrouter', return_value='AI reply')
	@patch('chat.views.generate_tts_file', return_value=b'mp3-bytes')
	def test_session_detail_without_tts_does_not_create_audio_message(self, mock_tts, _mock_ai):
		user = User.objects.create_user(username='tester2', password=self.password)
		session = ChatSession.objects.create(user=user, name='Session Text Only')
		self.client.force_login(user)

		response = self.client.post(
			reverse('session_detail', kwargs={'session_id': session.id}),
			{
				'message': 'Hello text only',
			},
		)

		self.assertEqual(response.status_code, 302)
		self.assertEqual(ChatMessage.objects.filter(session=session, role='assistant').count(), 1)
		self.assertEqual(AudioMessage.objects.filter(message__session=session).count(), 0)
		mock_tts.assert_not_called()
