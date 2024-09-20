import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets
from django.contrib.auth import authenticate
from django.db.models import Q
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from .serializers import UserRegistrationSerializer, LoginSerializer, UserSerializer, FriendRequestSerializer, BlockListSerializer
from .models import BlockList, User, FriendRequest
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from .permissions import IsAdmin, IsEditor, IsViewer
from django.conf import settings
from rest_framework import filters
from django.core.cache import cache

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
                refresh = RefreshToken.for_user(user)
                logger.info('User logged in successfully')
                return Response({
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'user': UserRegistrationSerializer(user).data}, status=status.HTTP_200_OK)
            
            logger.warning('Invalid credentials for user: %s', email)
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        
        logger.warning('User login failed: %s', serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserSearchView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsViewer]

    def get_queryset(self):
        search_query = self.request.query_params.get('search', '')
        logger.info('User search query: %s', search_query)
        current_user = self.request.user
        blocked_by_users = BlockList.objects.filter(blocked=current_user).values_list('blocker', flat=True)
        queryset = User.objects.filter(
            Q(email__iexact=search_query) | 
            Q(first_name__icontains=search_query) | 
            Q(last_name__icontains=search_query) |
            Q(username__icontains=search_query)
        ).exclude(id__in=blocked_by_users).order_by('id')
        logger.info('User search results count: %d', queryset.count())
        return queryset
    
class FriendRequestListAPIView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsViewer]
    serializer_class = FriendRequestSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['sent_at']

    def get_queryset(self):
        logger.info('Fetching pending friend requests for user: %s', self.request.user)
        return FriendRequest.objects.filter(receiver=self.request.user, status='pending').order_by('id')
    
class FriendRequestCreateAPIView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated, IsEditor]
    serializer_class = FriendRequestSerializer

    @transaction.atomic
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
        
        if BlockList.objects.filter(blocker=receiver, blocked=sender).exists():
            return Response({"error": "You are blocked by this user."}, status=status.HTTP_400_BAD_REQUEST)

        if BlockList.objects.filter(blocker=sender, blocked=receiver).exists():
            return Response({"error": "You have blocked this user."}, status=status.HTTP_400_BAD_REQUEST)

        if FriendRequest.objects.filter(sender=sender, receiver=receiver, status='pending').exists():
            logger.warning('Duplicate friend request attempt from user %s to user %s', sender_id, receiver_id)
            return Response({'error': "You have already sent a friend request to this user"}, status=status.HTTP_400_BAD_REQUEST)
        
        if FriendRequest.objects.filter(sender=receiver, receiver=sender, status='pending').exists():
            logger.warning('Pending friend request already exists from user %s to user %s', receiver_id, sender_id)
            return Response({'error': "You already have a pending friend request from this user"}, status=status.HTTP_400_BAD_REQUEST)
        
        if FriendRequest.objects.filter(sender=sender, receiver=receiver, status='accepted').exists():
            logger.warning('You are already friends with %s',receiver_id)
            return Response({'error': "You both are already friends"}, status=status.HTTP_400_BAD_REQUEST)
        
        if FriendRequest.objects.filter(sender=receiver, receiver=sender, status='accepted').exists():
            logger.warning('You are already friends with %s',receiver_id)
            return Response({'error': "You both are already friends"}, status=status.HTTP_400_BAD_REQUEST)
        
        cooldown_period = settings.FRC_HOURS
        one_day_ago = timezone.now() - timezone.timedelta(hours=cooldown_period)
        if FriendRequest.objects.filter(sender=sender, receiver=receiver, status='rejected', updated_at__gte=one_day_ago).exists():
            logger.warning(f'You cannot send request before {cooldown_period}Hrs')
            return Response({'error': f"You cannot send friend request before {cooldown_period}Hrs"}, status=status.HTTP_400_BAD_REQUEST)
        elif FriendRequest.objects.filter(sender=sender, receiver=receiver, status='rejected', updated_at__lte=one_day_ago).exists():
            FriendRequest.objects.filter(sender=sender, receiver=receiver, status='rejected', updated_at__lte=one_day_ago).delete()

        
        if FriendRequest.objects.filter(sender=receiver, receiver=sender, status='rejected', updated_at__gte=one_day_ago).exists():
            logger.warning(f'You cannot send request before {cooldown_period}Hrs')
            return Response({'error': f"You cannot send friend request before {cooldown_period}Hrs"}, status=status.HTTP_400_BAD_REQUEST)
        elif FriendRequest.objects.filter(sender=receiver, receiver=sender, status='rejected', updated_at__lte=one_day_ago).exists():
            FriendRequest.objects.filter(sender=receiver, receiver=sender, status='rejected', updated_at__lte=one_day_ago).delete()
        
        # Rate limiting (3 requests per minute)
        one_minute_ago = timezone.now() - timezone.timedelta(minutes=1)
        recent_requests = FriendRequest.objects.filter(sender_id=sender_id, sent_at__gte=one_minute_ago).count()
        if recent_requests >= 3:
            logger.warning('Rate limit exceeded for user %s', sender_id)
            return Response({'error': "You can send a maximum of 3 friend requests per minute."}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        friend_request, created = FriendRequest.objects.select_for_update().get_or_create(sender=sender, receiver=receiver)
        if not created:
            logger.warning('Friend request already sent from user %s to user %s', sender_id, receiver_id)
            return Response({"error": "Friend request already sent"})
        
        logger.info('Friend request created successfully from user %s to user %s', sender_id, receiver_id)
        return Response(FriendRequestSerializer(friend_request).data, status=status.HTTP_201_CREATED)

class FriendListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsViewer]
    serializer_class = UserSerializer

    def get_queryset(self):
        user = self.request.user
        cache_key = f'friend_list_{user.id}'
        cache_time = settings.CACHE_TTL

        queryset = cache.get(cache_key)

        if not queryset:
            logger.info('Cache miss: Fetching friend list for user: %s', user)
            queryset = User.objects.filter(
                Q(received_requests__sender=user, received_requests__status='accepted') | 
                Q(sent_requests__receiver=user, sent_requests__status='accepted')
            ).distinct().order_by('id')
            logger.info('Friend list fetched with %d friends', queryset.count())

            cache.set(cache_key, queryset, cache_time)
        else:
            logger.info('Cache hit: Returning cached friend list for user: %s', user)

        return queryset

class AcceptRejectFriendRequestView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated, IsEditor]
    serializer_class = FriendRequestSerializer
    queryset = FriendRequest.objects.all()

    @transaction.atomic
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


class BlockUnblockView(APIView):
    permission_classes = [IsAuthenticated, IsEditor]

    def post(self, request):
        logger.info("Block User request received")
        blocker = request.user
        serializer = BlockListSerializer(data=request.data)
        if serializer.is_valid():
            blocked_id = serializer.data.get('blocked_id')
            try:
                blocked = User.objects.get(id=blocked_id)
            except ObjectDoesNotExist:
                logger.error(f"User with id {blocked_id} does not exist")
                return Response({"error": "User does not exist."}, status=status.HTTP_404_NOT_FOUND)
            
            if blocked_id == blocker.id:
                logger.warning(f"User cannot block itself")
                return Response({"error": "User cannot block itself."}, status=status.HTTP_400_BAD_REQUEST)

            try:
                with transaction.atomic():
                    block, created = BlockList.objects.get_or_create(blocker=blocker, blocked=blocked)
                    if not created:
                        logger.warning(f"User {blocked_id} is already blocked by {blocker.id}")
                        return Response({"error": "User already blocked."}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                logger.error(f"Error blocking user {blocked_id}: {str(e)}")
                return Response({"error": "An error occurred while blocking the user."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            logger.info(f"User {blocked_id} blocked successfully by {blocker.id}")
            return Response(BlockListSerializer(block).data, status=status.HTTP_201_CREATED)
        
        logger.error(f"Invalid data: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        logger.info("Un-block User request received")
        blocker = request.user
        serializer = BlockListSerializer(data=request.data)
        if serializer.is_valid():
            blocked_id = serializer.validated_data.get('blocked_id')
            try:
                blocked = User.objects.get(id=blocked_id)
            except ObjectDoesNotExist:
                logger.error(f"User with id {blocked_id} does not exist")
                return Response({"error": "User does not exist."}, status=status.HTTP_404_NOT_FOUND)

            if blocked_id == blocker.id:
                logger.warning(f"User cannot unblock itself")
                return Response({"error": "User cannot unblock itself."}, status=status.HTTP_400_BAD_REQUEST)

            try:
                with transaction.atomic():
                    block_entry = BlockList.objects.filter(blocker=blocker, blocked=blocked)
                    if block_entry.exists():
                        block_entry.delete()
                    else:
                        logger.warning(f"User {blocked_id} is not blocked by {blocker.id}")
                        return Response({"error": "User is not blocked."}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                logger.error(f"Error unblocking user {blocked_id}: {str(e)}")
                return Response({"error": "An error occurred while unblocking the user."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            logger.info(f"User {blocked_id} unblocked successfully by {blocker.id}")
            return Response({"message": "User unblocked successfully."}, status=status.HTTP_200_OK)
        
        logger.error(f"Invalid data: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)