from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from company_lists.models import CompanyList
from company_lists.serializers import ListCompaniesCompactSerializer, ListInvitedGuestSerializer, ListInvitedUserSerializer
from shared.utils import CurrentUserProfileDefault, UIDRelatedFieldSerializer
from viral.models import Company, UserGuest, UserProfile


class ListOrCreateCompanyListsSerializer(serializers.ModelSerializer):
    is_smart_list = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    owner = serializers.HiddenField(
        default=serializers.CreateOnlyDefault(CurrentUserProfileDefault())
    )
    invited_users = UIDRelatedFieldSerializer(
        many=True,
        required=False,
        serializer=ListInvitedUserSerializer,
        queryset=UserProfile.objects.all(),
    )
    invited_guests = UIDRelatedFieldSerializer(
        many=True,
        required=False,
        serializer=ListInvitedGuestSerializer,
        queryset=UserGuest.objects.all(),
    )
    companies = UIDRelatedFieldSerializer(
        many=True,
        queryset=Company.objects.all(),
        serializer=ListCompaniesCompactSerializer
    )

    ERROR_INVALID_INVITED_USER = 'invalid_invited_user'

    default_error_messages = {
        ERROR_INVALID_INVITED_USER: _("Cannot add yourself as an invited user."),
    }

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

    def get_companies(self, company_list):
        companies_queryset = company_list.companies.all()
        # if company_list.company_list_type == CompanyList.COMPANY_LIST_TYPE_STATIC:
        #     companies_queryset = companies_queryset.filter(company_profile__user__emailaddress__verified=True)
        return ListCompaniesCompactSerializer(companies_queryset, many=True).data

    def validate(self, attrs):
        """
        Ensure that a owner cannot invite himself to his list.
        """
        attrs = super().validate(attrs)
        owner = attrs.get('owner', None)
        invited_users = attrs.get('invited_users', [])
        has_invited_himself = any(invitation.pk == owner.pk for invitation in invited_users)

        if has_invited_himself:
            raise serializers.ValidationError(self.ERROR_INVALID_INVITED_USER)
        return attrs

    def create(self, validated_data):
        """
        Create the company list and add companies to it.
        """
        companies = validated_data.pop('companies', [])
        company_list = super().create(validated_data)
        
        # Add companies to the list
        if companies:
            company_list.companies.add(*companies)
        
        return company_list

    def to_representation(self, instance):
        """
        Override to include companies data in the response.
        """
        data = super().to_representation(instance)
        data['companies'] = self.get_companies(instance)
        return data

    class Meta:
        model = CompanyList
        read_only_fields = ('created_at', 'updated_at')
        exclude = ('id', 'company_list_type', 'affiliate')
