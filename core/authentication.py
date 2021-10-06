# authentication.py
from rest_framework.authentication import TokenAuthentication, exceptions, _

from core.messages import validation_message


class CustomTokenAuthentication(TokenAuthentication):
    def authenticate_credentials(self, key):
        model = self.get_model()
        try:
            token = model.objects.select_related('user').get(key=key)
        except model.DoesNotExist:
            raise exceptions.AuthenticationFailed(_('Invalid token.'))
        if not token.user.is_active or token.user.is_deleted:  # Here I added something new !!
            # raise exceptions.AuthenticationFailed(_('User inactive or deleted.'))
            raise exceptions.AuthenticationFailed(_(validation_message.get('ACCOUNT_DEACTIVATED')))
        return (token.user, token)
