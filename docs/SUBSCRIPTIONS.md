# Subscriptions

Recently, subscription plans for Supporters were implemented in Abaca. This is supported by [Chargebee](https://www.chargebee.com/), a SaaS tool. They provide a Python library, which is what we use on the backend to integrate it in Abaca. In `/rest-api/settings.py` we grab the API key and the Site ID from environment variables and initialize the library with the following code:

```python
import chargebee

CHARGEBEE_KEY = os.environ.get('CHARGEBEE_KEY', '')
CHARGEBEE_SITE = os.environ.get('CHARGEBEE_SITE', '')

if CHARGEBEE := CHARGEBEE_KEY and CHARGEBEE_SITE:
	chargebee.configure(CHARGEBEE_KEY, CHARGEBEE_SITE)
```

Subscriptions are represented, in Abaca’s backend, by the `viral.models.Subscription` **model:

- `user` – the related `User` instance
- `customer_id` – Chargebee’s Customer unique identifier
- `subscription_id` – Chargebee’s Subscription unique identifier
- `plan_id` – Chargebee’s subscription plan unique identifier
- `start_date`
- `renewal_date`

Besides these properties, there is also a *class method* called `sync()` which relies on the Chargebee’s Python library to synchronize subscription data (i.e. customer ID, subscription ID, plan ID) with Chargebee, or create new Customer and Subscription records for Abaca users in Chargebee in case they do not exist yet.

Additionally, there’s the `update_company_details()` method, which we use to communicate changes to Chargebee whenever user updates their email or company name in Abaca.

Abaca’s API exposes a `/subscription/` endpoint that, when requested, if there is an existing subscription, calls the `sync()` method and returns the subscription data to the frontend. 

There are two additional endpoints – `/chargebee/portal/` and `/chargebee/checkout/` – which generate payloads required for Chargebee’s client-side integration that we also use. All subscription management, besides what is described in this document, is managed directly on the frontend.