from rest_framework import serializers

from company_lists.models import CompanyList
from company_lists.serializers import ListCompaniesCompactSerializer


class ListSharedCompanyListsSerializer(serializers.ModelSerializer):
    is_smart_list = serializers.SerializerMethodField()
    companies = serializers.SerializerMethodField()

    def get_is_smart_list(self, company_list):
        return company_list.company_list_type == CompanyList.COMPANY_LIST_TYPE_AFFILIATE_SUBMISSIONS

    def get_companies(self, company_list):
        companies_queryset = company_list.companies.all()
        if company_list.company_list_type == CompanyList.COMPANY_LIST_TYPE_STATIC:
            companies_queryset = companies_queryset.filter(company_profile__user__emailaddress__verified=True)
        return ListCompaniesCompactSerializer(companies_queryset, many=True).data

    class Meta:
        model = CompanyList
        fields = ('uid', 'title', 'description', 'companies', 'is_smart_list')
