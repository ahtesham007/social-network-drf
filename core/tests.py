from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from .models import User, FriendRequest

class UserRegistrationAPIViewTestCase(APITestCase):
    def test_user_registration_success(self):
        url = reverse('signup')
        data = {
            'email': 'testuser@example.com',
            'password': 'testpassword123',
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(User.objects.get().email, 'testuser@example.com')

    def test_user_registration_failure(self):
        url = reverse('signup')
        data = {
            'email': 'invalid-email',
            'password': 'testpassword123',
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class UserLoginAPIViewTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='testuser@example.com', password='testpassword123', username='testuser')

    def test_user_login_success(self):
        url = reverse('login')
        data = {
            'email': 'testuser@example.com',
            'password': 'testpassword123'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)

    def test_user_login_failure_invalid_credentials(self):
        url = reverse('login')
        data = {
            'email': 'testuser@example.com',
            'password': 'wrongpassword'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data['error'], 'Invalid credentials')

    def test_user_login_failure_user_not_exist(self):
        url = reverse('login')
        data = {
            'email': 'nonexistent@example.com',
            'password': 'testpassword123'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['error'], 'User does not exist')


class UserSearchViewTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='testuser@example.com', username='testuser', password='testpassword123', first_name='testuser')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_user_search(self):
        url = reverse('user-search')
        response = self.client.get(url, {'search': 'testuser'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['email'], 'testuser@example.com')


class FriendRequestCreateAPIViewTestCase(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(email='user1@example.com', password='password123', username='user1', first_name='user1')
        self.user2 = User.objects.create_user(email='user2@example.com', password='password123', username='user2', first_name='user2')
        self.user3 = User.objects.create_user(email='user3@example.com', password='password123', username='user3', first_name='user3')
        self.user4 = User.objects.create_user(email='user4@example.com', password='password123', username='user4', first_name='user4')
        self.user5 = User.objects.create_user(email='user5@example.com', password='password123', username='user5', first_name='user5')
        self.client.force_authenticate(user=self.user1)

    def test_create_friend_request_success(self):
        url = reverse('friend-request-list-create')
        data = {'receiver': self.user2.id}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(FriendRequest.objects.count(), 1)
        self.assertEqual(FriendRequest.objects.get().receiver, self.user2)

    def test_create_friend_request_to_self(self):
        url = reverse('friend-request-list-create')
        data = {'receiver': self.user1.id}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'You cannot send a friend request to yourself')

    def test_create_friend_request_receiver_not_found(self):
        url = reverse('friend-request-list-create')
        data = {'receiver': 999}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['error'], 'Receiver not found')

    def test_create_duplicate_friend_request(self):
        FriendRequest.objects.create(sender=self.user1, receiver=self.user2, status='pending')
        url = reverse('friend-request-list-create')
        data = {'receiver': self.user2.id}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'You have already sent a friend request to this user')

    def test_create_friend_request_rate_limit(self):
        users = [self.user2, self.user3, self.user4]
        for user in users:
            FriendRequest.objects.create(sender=self.user1, receiver=user, status='pending')
        url = reverse('friend-request-list-create')
        data = {'receiver': self.user5.id}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(response.data['error'], 'You can send a maximum of 3 friend requests per minute.')


class FriendListViewTestCase(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(email='user1@example.com', password='password123', username='user1', first_name='user1')
        self.user2 = User.objects.create_user(email='user2@example.com', password='password123', username='user2', first_name='user2')
        self.user3 = User.objects.create_user(email='user3@example.com', password='password123', username='user3', first_name='user3')
        FriendRequest.objects.create(sender=self.user1, receiver=self.user2, status='accepted')
        FriendRequest.objects.create(sender=self.user3, receiver=self.user1, status='accepted')
        self.client.force_authenticate(user=self.user1)

    def test_get_friend_list(self):
        url = reverse('friend-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]['email'], 'user2@example.com')
        self.assertEqual(response.data[1]['email'], 'user3@example.com')


class AcceptRejectFriendRequestViewTestCase(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(email='user1@example.com', password='password123', username='user1', first_name='user1')
        self.user2 = User.objects.create_user(email='user2@example.com', password='password123', username='user2', first_name='user2')
        self.friend_request = FriendRequest.objects.create(sender=self.user1, receiver=self.user2, status='pending')
        self.client.force_authenticate(user=self.user2)

    def test_accept_friend_request_success(self):
        url = reverse('accept-reject-friend-request', kwargs={'pk': self.friend_request.id})
        data = {'action': 'accepted'}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.friend_request.refresh_from_db()
        self.assertEqual(self.friend_request.status, 'accepted')

    def test_reject_friend_request_success(self):
        url = reverse('accept-reject-friend-request', kwargs={'pk': self.friend_request.id})
        data = {'action': 'rejected'}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.friend_request.refresh_from_db()
        self.assertEqual(self.friend_request.status, 'rejected')

    def test_unauthorized_friend_request_update(self):
        self.client.force_authenticate(user=self.user1)
        url = reverse('accept-reject-friend-request', kwargs={'pk': self.friend_request.id})
        data = {'action': 'accepted'}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['error'], 'You are not authorized to perform this action.')

    def test_invalid_action_update(self):
        url = reverse('accept-reject-friend-request', kwargs={'pk': self.friend_request.id})
        data = {'action': 'invalid_action'}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Invalid action update.')