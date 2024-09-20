from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import FriendRequest

@receiver(post_save, sender=FriendRequest)
@receiver(post_delete, sender=FriendRequest)
def clear_friend_list_cache(sender, instance, **kwargs):
    cache_key = f'friend_list_{instance.receiver.id}'
    cache.delete(cache_key)
    cache_key = f'friend_list_{instance.sender.id}'
    cache.delete(cache_key)
