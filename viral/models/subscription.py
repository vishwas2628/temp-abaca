import bugsnag
import chargebee
from django.db import models
from allauth.utils import get_user_model
from shared.models.timestamped_model import TimestampedModel
from datetime import datetime

from viral.models.company import Company


class Subscription(TimestampedModel):
    user = models.OneToOneField(get_user_model(), on_delete=models.CASCADE)
    customer_id = models.CharField(max_length=100, null=True, blank=True)
    subscription_id = models.CharField(max_length=100, null=True, blank=True)
    plan_id = models.CharField(max_length=100, null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    renewal_date = models.DateField(null=True, blank=True)

    @classmethod
    def sync(cls, user):
        # Make sure the user is a Supporter
        if user.userprofile.company.type != Company.SUPPORTER:
            raise ValueError("User is not a Supporter")

        try:
            # Check if there is already a customer in Chargebee for this user
            existing_customers = chargebee.Customer.list({"email[is]": user.email})

            if len(existing_customers) > 0:
                customer_data = existing_customers[0].customer
            else:
                # Create a new Chargebee customer
                customer_data = chargebee.Customer.create(
                    {
                        "email": user.email,
                        "company": user.userprofile.company.name,
                    }
                ).customer

            # Check if there is already a subscription in Chargebee for this user
            existing_subscriptions = chargebee.Subscription.list(
                {
                    "customer_id[is]": customer_data.id,
                    "status[is]": "active",
                }
            )

            if len(existing_subscriptions) > 0:
                subscription_data = existing_subscriptions[0].subscription
            else:
                # Create a new Chargebee subscription
                subscription_data = chargebee.Subscription.create_for_customer(
                    customer_data.id,
                    {
                        "plan_id": "supporter-free",
                    },
                ).subscription

            # Create or update the Subscription in the DB
            subscription, created = cls.objects.update_or_create(
                user=user,
                defaults={
                    "customer_id": customer_data.id,
                    "subscription_id": subscription_data.id,
                    "plan_id": subscription_data.plan_id,
                    "start_date": datetime.fromtimestamp(subscription_data.created_at).date(),
                    "renewal_date": datetime.fromtimestamp(subscription_data.next_billing_at).date(),
                },
            )

            return subscription

        except chargebee.APIError as error:
            bugsnag.notify(error)
            raise

    def update_company_details(self):
        try:
            chargebee.Customer.update(
                self.customer_id,
                {
                    'company': self.user.userprofile.company.name,
                    'email': self.user.email,
                },
            )
        except chargebee.APIError as error:
            bugsnag.notify(error)
