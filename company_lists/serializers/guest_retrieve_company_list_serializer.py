from rest_framework import serializers

from company_lists.models import CompanyList
from company_lists.serializers import ListCompaniesCompactSerializer
from viral.models import Company


class GuestRetrieveCompanyListSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    companies = ListCompaniesCompactSerializer(many=True)

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
        fields = ('uid', 'type', 'title', 'description', 'companies')
