from django.urls import path
from rest_framework_simplejwt import views as jwt_views
from .views import (
    UserRegistrationAPIView,
    UserLoginAPIView, 
    UserSearchView, 
    FriendRequestListAPIView,
    FriendRequestCreateAPIView,  
    FriendListView,
    AcceptRejectFriendRequestView,
    BlockUnblockView
)

urlpatterns = [
    path('signup/', UserRegistrationAPIView.as_view(), name='signup'),
    path('login/', UserLoginAPIView.as_view(), name='login'),
    path('token/refresh/', jwt_views.TokenRefreshView.as_view(), name='token_refresh'),
    path('user/', UserSearchView.as_view(), name='user-search'),
    path('friend-request/', FriendRequestCreateAPIView.as_view(), name='friend-request-list-create'),
    path('friend-requests/', FriendRequestListAPIView.as_view(), name='friend-request-list'),
    path('friends/', FriendListView.as_view(), name='friend-list'),
    path('friend-request-action/<int:pk>/', AcceptRejectFriendRequestView.as_view(), name='accept-reject-friend-request'),
    path('block/', BlockUnblockView.as_view(), name='block-unblock-user'),
]