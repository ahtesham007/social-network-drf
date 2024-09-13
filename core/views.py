import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from django.db.models import Q
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from .serializers import UserRegistrationSerializer, LoginSerializer, UserSerializer, FriendRequestSerializer
from .models import User, FriendRequest
from django.utils import timezone

logger = logging.getLogger(__name__)

class UserRegistrationAPIView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        logger.info('User registration attempt')
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            logger.info('User registered successfully')
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        logger.warning('User registration failed: %s', serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserLoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        logger.info('User login attempt')
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            email = request.data.get('email').lower()
            password = request.data.get('password')
            if not User.objects.filter(email=email).exists():
                logger.warning('User does not exist')
                return Response({'error': 'User does not exist'}, status=status.HTTP_404_NOT_FOUND)
            user = authenticate(email=email, password=password)
            if user:
                token, _ = Token.objects.get_or_create(user=user)
                logger.info('User logged in successfully')
                return Response({'token': token.key, 'user': UserRegistrationSerializer(user).data}, status=status.HTTP_200_OK)
            
            logger.warning('Invalid credentials for user: %s', email)
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        
        logger.warning('User login failed: %s', serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserSearchView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        search_query = self.request.query_params.get('search', '')
        logger.info('User search query: %s', search_query)
        queryset = User.objects.filter(
            Q(email__iexact=search_query) | 
            Q(first_name__icontains=search_query) | 
            Q(last_name__icontains=search_query)
        )
        logger.info('User search results count: %d', queryset.count())
        return queryset
    
class FriendRequestCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FriendRequestSerializer
    pagination_class = None

    def get_queryset(self):
        logger.info('Fetching pending friend requests for user: %s', self.request.user)
        return FriendRequest.objects.filter(receiver=self.request.user, status='pending')

    def create(self, request):
        logger.info('Friend request creation attempt by user: %s', self.request.user)
        sender = self.request.user
        sender_id = sender.id
        receiver_id = self.request.data.get('receiver')
        
        try:
            receiver = User.objects.get(id=receiver_id)
        except User.DoesNotExist:
            logger.warning('Receiver not found: %s', receiver_id)
            return Response({"error": "Receiver not found"}, status=status.HTTP_404_NOT_FOUND)
        
        if sender_id == receiver_id:
            logger.warning('User %s tried to send a friend request to themselves', sender_id)
            return Response({'error': 'You cannot send a friend request to yourself'}, status=status.HTTP_400_BAD_REQUEST)
        
        if FriendRequest.objects.filter(sender=sender, receiver=receiver, status='pending').exists():
            logger.warning('Duplicate friend request attempt from user %s to user %s', sender_id, receiver_id)
            return Response({'error': "You have already sent a friend request to this user"}, status=status.HTTP_400_BAD_REQUEST)
        
        if FriendRequest.objects.filter(sender=receiver, receiver=sender, status='pending').exists():
            logger.warning('Pending friend request already exists from user %s to user %s', receiver_id, sender_id)
            return Response({'error': "You already have a pending friend request from this user"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Rate limiting (3 requests per minute)
        one_minute_ago = timezone.now() - timezone.timedelta(minutes=1)
        recent_requests = FriendRequest.objects.filter(sender_id=sender_id, sent_at__gte=one_minute_ago).count()
        if recent_requests >= 3:
            logger.warning('Rate limit exceeded for user %s', sender_id)
            return Response({'error': "You can send a maximum of 3 friend requests per minute."}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        friend_request, created = FriendRequest.objects.get_or_create(sender=sender, receiver=receiver)
        if not created:
            logger.warning('Friend request already sent from user %s to user %s', sender_id, receiver_id)
            return Response({"error": "Friend request already sent"})
        
        logger.info('Friend request created successfully from user %s to user %s', sender_id, receiver_id)
        return Response(FriendRequestSerializer(friend_request).data, status=status.HTTP_201_CREATED)

class FriendListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    pagination_class = None

    def get_queryset(self):
        logger.info('Fetching friend list for user: %s', self.request.user)
        queryset = User.objects.filter(
            Q(received_requests__sender=self.request.user, received_requests__status='accepted') | 
            Q(sent_requests__receiver=self.request.user, sent_requests__status='accepted')
        ).distinct()
        logger.info('Friend list fetched with %d friends', queryset.count())
        return queryset

class AcceptRejectFriendRequestView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FriendRequestSerializer
    queryset = FriendRequest.objects.all()

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        logger.info('Friend request update attempt by user: %s', request.user)
        ACTIONS = ['accepted', 'rejected']
        
        if instance.receiver != request.user:
            logger.warning('Unauthorized friend request update attempt by user: %s', request.user)
            return Response({"error": "You are not authorized to perform this action."}, status=status.HTTP_403_FORBIDDEN)
        
        if instance.status in ACTIONS:
            logger.warning('Friend request status is already updated to %s', instance.status)
            return Response({"error": f"Friend request status is already {instance.status}"}, status=status.HTTP_406_NOT_ACCEPTABLE)

        new_status = request.data.get('action', None)
        if new_status in ACTIONS:
            instance.status = new_status
            instance.save()
            logger.info('Friend request %s updated to %s by user %s', instance.id, new_status, request.user)
            return Response(self.get_serializer(instance).data)
        else:
            logger.warning('Invalid action update attempt by user: %s', request.user)
            return Response({"error": "Invalid action update."}, status=status.HTTP_400_BAD_REQUEST)