from django.http import Http404

from rest_framework.mixins import CreateModelMixin
from rest_framework.viewsets import GenericViewSet

from olympia.abuse.serializers import (
    AddonAbuseReportSerializer,
    UserAbuseReportSerializer,
)
from olympia.accounts.views import AccountViewSet
from olympia.addons.views import AddonViewSet
from olympia.api.throttling import GranularIPRateThrottle, GranularUserRateThrottle


class AbuseUserThrottle(GranularUserRateThrottle):
    rate = '20/day'
    scope = 'user_abuse'


class AbuseIPThrottle(GranularIPRateThrottle):
    rate = '20/day'
    scope = 'ip_abuse'


class AddonAbuseViewSet(CreateModelMixin, GenericViewSet):
    permission_classes = []
    serializer_class = AddonAbuseReportSerializer
    throttle_classes = (AbuseUserThrottle, AbuseIPThrottle)

    def get_addon_viewset(self):
        if hasattr(self, 'addon_viewset'):
            return self.addon_viewset

        if 'addon_pk' not in self.kwargs:
            self.kwargs['addon_pk'] = self.request.data.get(
                'addon'
            ) or self.request.GET.get('addon')
        self.addon_viewset = AddonViewSet(
            request=self.request,
            permission_classes=[],
            kwargs={'pk': self.kwargs['addon_pk']},
            action='retrieve_from_related',
        )
        return self.addon_viewset

    def get_addon_object(self):
        if hasattr(self, 'addon_object'):
            return self.addon_object

        self.addon_object = self.get_addon_viewset().get_object()
        if self.addon_object and not self.addon_object.is_public():
            raise Http404
        return self.addon_object

    def get_guid_and_addon(self):
        data = {
            'guid': None,
            'addon': None,
        }
        # See if the addon parameter looks like a guid. If it does, record the
        # guid without trying linking to an add-on in the database.
        if self.get_addon_viewset().get_lookup_field(self.kwargs['addon_pk']) == 'guid':
            data['guid'] = self.kwargs['addon_pk']
            # So that get_addon_object() doesn't raise a 404.
            self.addon_object = None
        # At this point get_addon_object() will either return None because we
        # set self.addon_object earlier, or find an add-on with its pk/slug,
        # or raise a 404.
        data['addon'] = self.get_addon_object()
        if data['addon']:
            # If we did find an add-on in database, regardless of how, make
            # sure we always store the guid as well.
            data['guid'] = data['addon'].guid
        return data


class UserAbuseViewSet(CreateModelMixin, GenericViewSet):
    permission_classes = []
    serializer_class = UserAbuseReportSerializer
    throttle_classes = (AbuseUserThrottle, AbuseIPThrottle)

    def get_user_object(self):
        if hasattr(self, 'user_object'):
            return self.user_object

        if 'user_pk' not in self.kwargs:
            self.kwargs['user_pk'] = self.request.data.get(
                'user'
            ) or self.request.GET.get('user')

        return AccountViewSet(
            request=self.request,
            permission_classes=[],
            kwargs={'pk': self.kwargs['user_pk']},
        ).get_object()
