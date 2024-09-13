from django.urls import path
from .views import (
    UserRegistrationAPIView,
    UserLoginAPIView, 
    UserSearchView, 
    FriendRequestCreateAPIView,  
    FriendListView,
    AcceptRejectFriendRequestView
)

urlpatterns = [
    path('signup/', UserRegistrationAPIView.as_view(), name='signup'),
    path('login/', UserLoginAPIView.as_view(), name='login'),
    path('user/', UserSearchView.as_view(), name='user-search'),
    path('friend-requests/', FriendRequestCreateAPIView.as_view(), name='friend-request-list-create'),
    path('friends/', FriendListView.as_view(), name='friend-list'),
    path('friend-request-action/<int:pk>/', AcceptRejectFriendRequestView.as_view(), name='accept-reject-friend-request'),
]