"""Payments and their details stay in the user's districts (OP-3322)."""

import json

from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.test import override_settings

from contribution.test_helpers import create_test_premium
from core.models.openimis_graphql_test_case import openIMISGraphQLTestCase, BaseTestContext
from core.test_helpers import create_right_only_user
from insuree.test_helpers import create_test_insuree
from location.models import Location
from location.test_helpers import create_basic_test_locations
from payment.gql_mutations import DeletePaymentsMutation, on_policy_mutation
from payment.models import Payment, PaymentDetail
from payment.services import update_or_create_payment, update_or_create_payment_detail
from payment.test_helpers import create_test_payment2
from policy.test_helpers import create_test_policy
from product.test_helpers import create_test_product

DETAILS_QUERY = "query { paymentDetails { edges { node { id payment { uuid } } } } }"
BY_PREMIUMS_QUERY = 'query { paymentsByPremiums(premiumUuids: ["%s", "%s"]) { edges { node { uuid } } } }'


@override_settings(ROW_SECURITY=True)
class PaymentRowScopeTests(openIMISGraphQLTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        create_basic_test_locations()
        product = create_test_product("OP3322Y")
        cls.policies, cls.premiums, cls.payments, cls.details = {}, {}, {}, {}
        for key, village_code in (("a", "R1D1M1V1"), ("b", "R2D1M1V1")):
            village = Location.objects.get(code=village_code, validity_to__isnull=True)
            insuree = create_test_insuree(
                with_family=True,
                is_head=True,
                custom_props={"current_village": village},
                family_custom_props={"location": village},
            )
            cls.policies[key] = create_test_policy(product, insuree, link=True)
            cls.premiums[key] = create_test_premium(cls.policies[key].id, with_payer=False)
            cls.payments[key], cls.details[key] = create_test_payment2(
                insuree_code=insuree.chf_id,
                product_code=product.code,
                detail_custom_props={"premium": cls.premiums[key]},
            )
        # Received but not matched to any premium yet: nothing to scope it by.
        cls.payments["unmatched"], cls.details["unmatched"] = create_test_payment2()
        cls.user = create_right_only_user(
            "op3322pay",
            [
                "gql_query_payments_perms",
                "gql_mutation_create_payments_perms",
                "gql_mutation_update_payments_perms",
                "gql_mutation_delete_payments_perms",
                "gql_mutation_delete_policies_perms",
            ],
            district_codes=["R1D1"],
        )
        cache.clear()

    def setUp(self):
        # Model instances are cached; a rolled-back change must not be read back.
        cache.clear()

    def _ours(self, model, rows):
        mine = {getattr(self, f"{model}s")[k].id: k for k in ("a", "b", "unmatched")}
        return {mine[r.id] for r in rows if r.id in mine}

    def _gql(self, query):
        token = BaseTestContext(user=self.user).get_jwt()
        response = self.query(query, headers={"HTTP_AUTHORIZATION": f"Bearer {token}"})
        content = json.loads(response.content)
        self.assertIsNone(content.get("errors"), content.get("errors"))
        return content["data"]

    # row scope on the models

    def test_payments_keep_own_district(self):
        rows = Payment.get_queryset(Payment.objects.all(), self.user)
        self.assertEqual(self._ours("payment", rows), {"a", "unmatched"})

    def test_payment_details_keep_own_district(self):
        rows = PaymentDetail.get_queryset(PaymentDetail.objects.all(), self.user)
        self.assertEqual(self._ours("detail", rows), {"a", "unmatched"})

    def test_anonymous_sees_nothing(self):
        self.assertFalse(Payment.get_queryset(Payment.objects.all(), AnonymousUser()).exists())
        self.assertFalse(
            PaymentDetail.get_queryset(PaymentDetail.objects.all(), AnonymousUser()).exists()
        )

    # GraphQL

    def test_payment_details_query_is_scoped(self):
        edges = self._gql(DETAILS_QUERY)["paymentDetails"]["edges"]
        uuids = {e["node"]["payment"]["uuid"].upper() for e in edges}
        self.assertIn(str(self.payments["a"].uuid).upper(), uuids)
        self.assertNotIn(str(self.payments["b"].uuid).upper(), uuids)

    def test_payments_by_premiums_is_scoped(self):
        data = self._gql(BY_PREMIUMS_QUERY % (self.premiums["a"].uuid, self.premiums["b"].uuid))
        uuids = {e["node"]["uuid"].upper() for e in data["paymentsByPremiums"]["edges"]}
        self.assertEqual(uuids, {str(self.payments["a"].uuid).upper()})

    # mutations and services

    def test_update_by_uuid_outside_the_scope_is_refused(self):
        with self.assertRaises(Payment.DoesNotExist):
            update_or_create_payment(
                {"uuid": self.payments["b"].uuid, "received_amount": 1}, self.user
            )

    def test_client_id_cannot_overwrite_a_payment(self):
        target = self.payments["b"]
        payment = update_or_create_payment({"id": target.id, "received_amount": 1}, self.user)

        self.assertNotEqual(payment.id, target.id)
        target.refresh_from_db()
        self.assertEqual(str(target.received_amount), "1000.00")

    def test_matching_a_premium_outside_the_scope_is_refused(self):
        from contribution.models import Premium

        with self.assertRaises(Premium.DoesNotExist):
            update_or_create_payment_detail(
                self.payments["unmatched"], self.premiums["b"].uuid, self.user
            )
        self.assertFalse(
            PaymentDetail.objects.filter(premium=self.premiums["b"])
            .exclude(id=self.details["b"].id)
            .exists()
        )

    def test_delete_outside_the_scope_is_refused(self):
        DeletePaymentsMutation.async_mutate(self.user, uuids=[self.payments["b"].uuid])

        self.assertIsNone(Payment.objects.get(id=self.payments["b"].id).validity_to)

    def test_policy_delete_handler_only_detaches_details_in_scope(self):
        on_policy_mutation(
            sender=None,
            mutation_class="DeletePoliciesMutation",
            data={"uuids": [self.policies["a"].uuid, self.policies["b"].uuid]},
            user=self.user,
        )

        self.assertIsNone(PaymentDetail.objects.get(id=self.details["a"].id).premium_id)
        self.assertEqual(
            PaymentDetail.objects.get(id=self.details["b"].id).premium_id, self.premiums["b"].id
        )

    def test_policy_delete_handler_requires_the_policy_delete_right(self):
        reader = create_right_only_user(
            "op3322payr", ["gql_query_payments_perms"], district_codes=["R1D1", "R2D1"]
        )
        on_policy_mutation(
            sender=None,
            mutation_class="DeletePoliciesMutation",
            data={"uuids": [self.policies["a"].uuid]},
            user=reader,
        )

        self.assertEqual(
            PaymentDetail.objects.get(id=self.details["a"].id).premium_id, self.premiums["a"].id
        )
