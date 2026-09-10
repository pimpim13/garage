from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class CaseInsensitiveModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        if username is None or password is None:
            return None
        try:
            user = UserModel._default_manager.get(**{f'{UserModel.USERNAME_FIELD}__iexact': username})
        except UserModel.DoesNotExist:
            UserModel().set_password(password)
            return None
        except UserModel.MultipleObjectsReturned:
            user = UserModel._default_manager.filter(
                **{f'{UserModel.USERNAME_FIELD}__iexact': username}
            ).order_by('id').first()
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
