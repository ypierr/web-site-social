from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from account.models import Profile, Contact
from images.models import Image

User = get_user_model()

class FluxosSociaisTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('ana', 'ana@example.com', 'senha-teste-123')
        self.other = User.objects.create_user('bia', 'bia@example.com', 'senha-teste-456')
        Profile.objects.create(user=self.user)
        Profile.objects.create(user=self.other)

    def test_cadastro_cria_perfil_e_hash(self):
        response = self.client.post(reverse('register'), {'username':'caio','first_name':'Caio','email':'caio@example.com','password':'senha-teste-789','password2':'senha-teste-789'})
        self.assertEqual(response.status_code, 200)
        user = User.objects.get(username='caio')
        self.assertTrue(user.check_password('senha-teste-789'))
        self.assertTrue(Profile.objects.filter(user=user).exists())

    def test_cadastro_rejeita_email_existente(self):
        self.client.post(reverse('register'), {'username':'caio','email':'ana@example.com','password':'abc','password2':'abc'})
        self.assertFalse(User.objects.filter(username='caio').exists())

    def test_login_email_e_conta_inativa(self):
        self.assertTrue(self.client.login(username='ana@example.com', password='senha-teste-123'))
        self.client.logout()
        self.user.is_active = False
        self.user.save()
        self.assertFalse(self.client.login(username='ana@example.com', password='senha-teste-123'))

    def test_acesso_restrito(self):
        self.assertEqual(self.client.get(reverse('edit')).status_code, 302)
        self.assertEqual(self.client.post(reverse('images:like'), {}).status_code, 302)

    def test_seguir_e_deixar_de_seguir(self):
        self.client.force_login(self.user)
        for action, expected in [('follow', True), ('unfollow', False)]:
            response = self.client.post(reverse('user_follow'), {'id':self.other.pk,'action':action})
            self.assertEqual(response.json()['status'], 'ok')
            self.assertEqual(Contact.objects.filter(user_from=self.user,user_to=self.other).exists(), expected)

    def test_curtidas_atualizam_contador(self):
        image = Image.objects.create(user=self.other,title='Imagem',url='https://example.com/foto.jpg',image='teste.jpg')
        self.client.force_login(self.user)
        for action, total in [('like',1),('unlike',0)]:
            self.assertEqual(self.client.post(reverse('images:like'), {'id':image.pk,'action':action}).json()['status'],'ok')
            image.refresh_from_db()
            self.assertEqual(image.total_likes,total)

    @patch('images.views.r')
    def test_detalhe_conta_visualizacao(self, redis):
        redis.incr.return_value = 1
        image = Image.objects.create(user=self.user,title='Imagem',url='https://example.com/foto.jpg',image='teste.jpg')
        response = self.client.get(image.get_absolute_url())
        self.assertEqual(response.status_code,200)
        redis.incr.assert_called_once_with(f'image:{image.pk}:views')
        redis.zincrby.assert_called_once_with('image_ranking',1,image.pk)

