from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from .models import BlockList, User, FriendRequest

class UserRegistrationAPIViewTestCase(APITestCase):
    def test_user_registration_success(self):
        url = reverse('signup')
        data = {
            'email': 'testuser@example.com',
            'password': 'testpassword123',
            'username': 'testuser',
            'role':'editor',
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
        self.assertIn('access', response.data)

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


class UserSearchViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='user1@example.com', password='password123', username='user1', first_name='user1')
        self.client.login(email='user1@example.com', password='password123')
        self.client.force_authenticate(user=self.user)
        self.search_url = reverse('user-search')

    def test_search_user_by_email(self):
        User.objects.create_user(email='user2@example.com', password='password123', username='user2', first_name='user2')
        response = self.client.get(self.search_url, {'search': 'user2@example.com'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_search_user_by_first_name(self):
        User.objects.create_user(email='user2@example.com', password='password123', username='user2', first_name='John')
        response = self.client.get(self.search_url, {'search': 'John'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_search_user_by_last_name(self):
        User.objects.create_user(email='user3@example.com', password='password123', username='user3', first_name='user3',  last_name='Doe')
        response = self.client.get(self.search_url, {'search': 'Doe'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_search_excludes_blocked_users(self):
        blocked_user = User.objects.create_user(email='user4@example.com', password='password123', username='blockeduser', first_name='user4')
        BlockList.objects.create(blocker=blocked_user, blocked=self.user)
        response = self.client.get(self.search_url, {'search': 'blockeduser'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)


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
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['email'], 'user2@example.com')
        self.assertEqual(response.data['results'][1]['email'], 'user3@example.com')


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

class BlockUnblockViewTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(email='user1@example.com', password='password123', username='user1', first_name='user1')
        self.user2 = User.objects.create_user(email='user2@example.com', password='password123', username='user2', first_name='user2')
        self.block_url = reverse('block-unblock-user')

    def test_block_user(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.post(self.block_url, {'blocked_id': self.user2.id})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(BlockList.objects.filter(blocker=self.user1, blocked=self.user2).exists())

    def test_block_nonexistent_user(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.post(self.block_url, {'blocked_id': 999})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_block_self(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.post(self.block_url, {'blocked_id': self.user1.id})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_block_already_blocked_user(self):
        self.client.force_authenticate(user=self.user1)
        BlockList.objects.create(blocker=self.user1, blocked=self.user2)
        response = self.client.post(self.block_url, {'blocked_id': self.user2.id})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unblock_user(self):
        self.client.force_authenticate(user=self.user1)
        BlockList.objects.create(blocker=self.user1, blocked=self.user2)
        response = self.client.delete(self.block_url, {'blocked_id': self.user2.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(BlockList.objects.filter(blocker=self.user1, blocked=self.user2).exists())

    def test_unblock_nonexistent_user(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.delete(self.block_url, {'blocked_id': 999})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unblock_self(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.delete(self.block_url, {'blocked_id': self.user1.id})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unblock_not_blocked_user(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.delete(self.block_url, {'blocked_id': self.user2.id})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

class FriendRequestListAPIViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='user1@example.com', password='password123', username='user1', first_name='user1')
        self.client.login(username='testuser', password='testpass')
        self.client.force_authenticate(user=self.user)
        self.friend_request_url = reverse('friend-request-list')

    def test_get_pending_friend_requests(self):
        sender = User.objects.create_user(email='user2@example.com', password='password123', username='sender', first_name='user2')
        FriendRequest.objects.create(sender=sender, receiver=self.user, status='pending')
        response = self.client.get(self.friend_request_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_no_pending_friend_requests(self):
        response = self.client.get(self.friend_request_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)

    def test_ordering_of_friend_requests(self):
        sender1 = User.objects.create_user(email='user2@example.com', password='password123', username='sender1', first_name='sender1')
        sender2 = User.objects.create_user(email='user3@example.com', password='password123', username='sender2', first_name='sender2')
        FriendRequest.objects.create(sender=sender1, receiver=self.user, status='pending', sent_at='2023-01-01')
        FriendRequest.objects.create(sender=sender2, receiver=self.user, status='pending', sent_at='2023-01-02')
        response = self.client.get(self.friend_request_url, {'ordering': 'sent_at'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'][0]['id'], 13)
        self.assertEqual(response.data['results'][1]['id'], 14)