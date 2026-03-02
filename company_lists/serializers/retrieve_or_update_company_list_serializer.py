from rest_framework import serializers

from company_lists.models import CompanyList
from company_lists.serializers import (ListCompaniesCompactSerializer,
                                       ListInvitedGuestSerializer,
                                       ListInvitedUserSerializer)

from shared.utils import UIDRelatedFieldSerializer
from viral.models import Company, UserGuest, UserProfile


class RetrieveOrUpdateCompanyListSerializer(serializers.ModelSerializer):
    is_smart_list = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    invited_users = UIDRelatedFieldSerializer(
        many=True,
        serializer=ListInvitedUserSerializer,
        queryset=UserProfile.objects.all(),
    )
    invited_guests = UIDRelatedFieldSerializer(
        many=True,
        serializer=ListInvitedGuestSerializer,
        queryset=UserGuest.objects.all(),
    )
    companies = UIDRelatedFieldSerializer(
        many=True,
        serializer=ListCompaniesCompactSerializer,
        queryset=Company.objects.all()
    )

    def get_is_smart_list(self, company_list):
        return company_list.company_list_type == CompanyList.COMPANY_LIST_TYPE_AFFILIATE_SUBMISSIONS

    def get_is_owner(self, company_list):
        user = self.context['request'].user
        if company_list.company_list_type == CompanyList.COMPANY_LIST_TYPE_AFFILIATE_SUBMISSIONS:
            affiliate_company = company_list.affiliate.company
            return user.userprofile.supporter.first() in company_list.affiliate.supporters.all() or (
                affiliate_company and affiliate_company.company_profile.user == user)
        else:
            return company_list.owner.user == user

    def get_type(self, company_list):
        """
        Determine companies type based on the opposite owner type:
        (Entrepreneur <=> Supporter)
        """
        if company_list.company_list_type == CompanyList.COMPANY_LIST_TYPE_AFFILIATE_SUBMISSIONS:
            return company_list.affiliate.flow_target
        else:
            return Company.SUPPORTER if company_list.owner.company.type == Company.ENTREPRENEUR else Company.ENTREPRENEUR

    class Meta:
        model = CompanyList
        read_only_fields = ('created_at', 'updated_at')
        exclude = ('id', 'owner', 'company_list_type', 'affiliate')
