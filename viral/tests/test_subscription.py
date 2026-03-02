from os import name
from time import time
from unittest.mock import MagicMock, patch
from django.contrib.auth import get_user_model
from matching.models.supporter import Supporter
from shared.utils import AbacaAPITestCase
from viral.models.company import Company
from viral.models.subscription import Subscription
from viral.models.user_profile import UserProfile


class SubscriptionTestCase(AbacaAPITestCase):
    def setUp(self):
        super().setUp()
        name = "Subscription Test"
        email = "subscription-test@abaca.app"
        self.user = get_user_model().objects.create_user(username="subscription-test", email=email)
        self.company = Company.objects.create(name=name, email=email, type=Company.SUPPORTER)
        self.user_profile = UserProfile.objects.create(user=self.user, company=self.company)
        self.supporter = Supporter.objects.create(
            name=name, email=email, user_profile=self.user_profile, investing_level_range=[1, 10]
        )

    def test_no_subscription_upon_supporter_creation(self):
        self.assertEqual(Subscription.objects.filter(user=self.user).count(), 0)

    @patch("viral.models.subscription.chargebee.Subscription.list")
    @patch("viral.models.subscription.chargebee.Subscription.create_with_items")
    @patch("viral.models.subscription.chargebee.Customer.list")
    @patch("viral.models.subscription.chargebee.Customer.create")
    def test_subscription_setup_with_no_existing_customer(
        self, customer_create_mock, customer_list_mock, subscription_create_mock, subscription_list_mock
    ):
        customer_create_mock.return_value.customer.id = "JFW927"
        customer_list_mock.return_value = []
        subscription_create_mock.return_value.subscription.id = "HDY283"
        subscription_create_mock.return_value.subscription.subscription_items[0].item_price_id = "free-USD-Yearly"
        subscription_create_mock.return_value.subscription.created_at = time()
        subscription_create_mock.return_value.subscription.next_billing_at = time()
        subscription_list_mock.return_value = []
        subscription = Subscription.setup(self.user)
        self.assertEqual(Subscription.objects.filter(user=self.user).count(), 1)
        # Run setup() again to make sure it doesn't create a duplicate
        subscription = Subscription.setup(self.user)
        self.assertEqual(Subscription.objects.filter(user=self.user).count(), 1)
        if not isinstance(subscription, Subscription):
            self.fail("Subscription.setup() did not return a Subscription object")
        self.assertEqual(subscription.user, self.user)
        self.assertEqual(subscription.customer_id, "JFW927")
        self.assertEqual(subscription.subscription_id, "HDY283")
        self.assertEqual(subscription.plan_id, "free-USD-Yearly")

    @patch("viral.models.subscription.chargebee.Subscription.list")
    @patch("viral.models.subscription.chargebee.Subscription.create_with_items")
    @patch("viral.models.subscription.chargebee.Customer.list")
    def test_subscription_setup_with_existing_customer_and_no_subscription(
        self, customer_list_mock, subscription_create_mock, subscription_list_mock
    ):
        customer_list_mock.return_value = [MagicMock()]
        customer_list_mock.return_value[0].customer.id = "JFW927"
        subscription_create_mock.return_value.subscription.id = "HDY283"
        subscription_create_mock.return_value.subscription.subscription_items[0].item_price_id = "free-USD-Yearly"
        subscription_create_mock.return_value.subscription.created_at = time()
        subscription_create_mock.return_value.subscription.next_billing_at = time()
        subscription_list_mock.return_value = []
        subscription = Subscription.setup(self.user)
        self.assertEqual(Subscription.objects.filter(user=self.user).count(), 1)
        # Run setup() again to make sure it doesn't create a duplicate
        subscription = Subscription.setup(self.user)
        self.assertEqual(Subscription.objects.filter(user=self.user).count(), 1)
        if not isinstance(subscription, Subscription):
            self.fail("Subscription.setup() did not return a Subscription object")
        self.assertEqual(subscription.user, self.user)
        self.assertEqual(subscription.customer_id, "JFW927")
        self.assertEqual(subscription.subscription_id, "HDY283")
        self.assertEqual(subscription.plan_id, "free-USD-Yearly")

    @patch("viral.models.subscription.chargebee.Subscription.list")
    @patch("viral.models.subscription.chargebee.Customer.list")
    def test_subscription_setup_with_existing_customer_and_subscription(
        self, customer_list_mock, subscription_list_mock
    ):
        customer_list_mock.return_value = [MagicMock()]
        customer_list_mock.return_value[0].customer.id = "JFW927"
        subscription_list_mock.return_value = [MagicMock()]
        subscription_list_mock.return_value[0].subscription.id = "HDY283"
        subscription_list_mock.return_value[0].subscription.subscription_items[0].item_price_id = "free-USD-Yearly"
        subscription_list_mock.return_value[0].subscription.created_at = time()
        subscription_list_mock.return_value[0].subscription.next_billing_at = time()
        subscription = Subscription.setup(self.user)
        self.assertEqual(Subscription.objects.filter(user=self.user).count(), 1)
        # Run setup() again to make sure it doesn't create a duplicate
        subscription = Subscription.setup(self.user)
        self.assertEqual(Subscription.objects.filter(user=self.user).count(), 1)
        if not isinstance(subscription, Subscription):
            self.fail("Subscription.setup() did not return a Subscription object")
        self.assertEqual(subscription.user, self.user)
        self.assertEqual(subscription.customer_id, "JFW927")
        self.assertEqual(subscription.subscription_id, "HDY283")
        self.assertEqual(subscription.plan_id, "free-USD-Yearly")
